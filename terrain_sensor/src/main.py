"""Service entry point for terrain observation and event processing."""

import asyncio
import json
import logging
from typing import Any, Dict

import aiomqtt
from common.parameters import (
    ENV_TELEMETRY_TOPIC,
    FIELD_INIT_MOIST,
    FIELD_INIT_OXY,
    FIELD_INIT_TYPE,
    FIELD_NAME,
    SOIL_LAYOUT_SEED,
    MQTT_KEEPALIVE,
    MQTT_QOS,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    MQTT_RECONNECT_SECONDS,
    TERRAIN_CMD_TOPIC,
    TERRAIN_EVENT_TOPIC,
)
from core.irrigation import apply_irrigation
from core.soil_type import select_initial_soil
from core.terrain_condition import (
    create_terrain_state,
    process_terrain_update,
    terrain_telemetry,
)
from utils.logger_utils import LoggingUtils
from utils.mqtt_utils import Deduper, build_tls_context, publish_json

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)

INITIAL_SOIL_TYPE = select_initial_soil(
    FIELD_NAME,
    FIELD_INIT_TYPE,
    SOIL_LAYOUT_SEED,
)


async def publish_terrain(client: aiomqtt.Client, camp_id: str, state: Dict[str, Any]) -> None:
    """Publish the current observed terrain state."""
    await publish_json(
        client,
        f"camp/{camp_id}/terrain/telemetry",
        terrain_telemetry(state),
        qos=MQTT_QOS,
    )


async def listen_mqtt_telemetry(
    client: aiomqtt.Client,
    camp_states: Dict[str, Dict[str, Any]],
    dedup: Deduper,
) -> None:
    """Observe ambient changes, actuator events and administrative commands."""
    await client.subscribe(ENV_TELEMETRY_TOPIC, qos=MQTT_QOS)
    await client.subscribe(TERRAIN_EVENT_TOPIC, qos=MQTT_QOS)
    await client.subscribe(TERRAIN_CMD_TOPIC, qos=MQTT_QOS)

    logger.info(
        "Terrain Sensor ready | field=%s | soil=%s | ambient=%s | events=%s",
        FIELD_NAME,
        INITIAL_SOIL_TYPE,
        ENV_TELEMETRY_TOPIC,
        TERRAIN_EVENT_TOPIC,
    )

    async for msg in client.messages:
        topic = str(msg.topic)
        raw = (
            msg.payload.decode("utf-8")
            if isinstance(msg.payload, bytes)
            else str(msg.payload)
        )

        parts = topic.split("/")
        if len(parts) < 2 or parts[0] != "camp":
            continue
        camp_id = parts[1]

        if camp_id not in camp_states:
            camp_states[camp_id] = create_terrain_state(
                initial_moisture=FIELD_INIT_MOIST,
                initial_oxygen=FIELD_INIT_OXY,
                soil_type=INITIAL_SOIL_TYPE,
            )

        state = camp_states[camp_id]

        try:
            if "environment/telemetry" in topic:
                ambient_data = json.loads(raw)
                if dedup.is_duplicate_or_stale(topic, ambient_data.get("ts")):
                    continue

                telemetry = process_terrain_update(state, ambient_data)
                await publish_json(
                    client,
                    f"camp/{camp_id}/terrain/telemetry",
                    telemetry,
                    qos=MQTT_QOS,
                )

                logger.info(
                    "[%s] [%s] Soil=%s | moisture=%.1f%% | O2=%.1f%%",
                    camp_id.upper(),
                    telemetry.get("date"),
                    telemetry.get("soil_type", "Franco"),
                    telemetry.get("soil_moisture", 0.0),
                    telemetry.get("oxygenation", 0.0),
                )

            elif "terrain/event/" in topic:
                event = topic.split("terrain/event/")[-1].lower()
                event_data = json.loads(raw) if raw else {}
                request_id = event_data.get("request_id")

                if event == "irrigated":
                    amount = float(event_data.get("amount", 0.0))
                    state["soil_moisture"] = apply_irrigation(
                        state["soil_moisture"], amount
                    )
                    state["water_dispensed_mm"] = amount
                    state["last_irrigation_amount_pct"] = amount
                    state["last_irrigation_id"] = request_id
                    state["last_action"] = "irrigated"

                    logger.info(
                        "[%s] Observed completed irrigation | request=%s | "
                        "amount=%.1f | moisture=%.1f%%",
                        camp_id.upper(),
                        request_id,
                        amount,
                        state["soil_moisture"],
                    )

                elif event == "reoxygenated":
                    state["oxygenation"] = float(
                        event_data.get("oxygenation", 100.0)
                    )
                    state["last_reoxygenation_id"] = request_id
                    state["last_action"] = "reoxygenated"

                    logger.info(
                        "[%s] Observed completed reoxygenation | request=%s | O2=%.1f%%",
                        camp_id.upper(),
                        request_id,
                        state["oxygenation"],
                    )
                else:
                    continue

                await publish_terrain(client, camp_id, state)

            elif "terrain/cmd/" in topic:
                # Administrative sensor commands only. Irrigation and
                # reoxygenation are intentionally NOT handled here.
                cmd = topic.split("terrain/cmd/")[-1].lower()

                if cmd in ("set_soil_type", "set_type"):
                    state["soil_type"] = raw.strip()
                    logger.info(
                        "[%s] Soil type set to %s",
                        camp_id.upper(),
                        state["soil_type"],
                    )

                elif cmd in ("reset", "restart"):
                    camp_states[camp_id] = create_terrain_state(
                        initial_moisture=FIELD_INIT_MOIST,
                        initial_oxygen=FIELD_INIT_OXY,
                        soil_type=INITIAL_SOIL_TYPE,
                    )
                    state = camp_states[camp_id]
                    dedup.reset()
                    logger.info("[%s] Terrain observation state reset.", camp_id.upper())
                else:
                    logger.warning(
                        "[%s] Unsupported Terrain Sensor command ignored: %s",
                        camp_id.upper(),
                        cmd,
                    )
                    continue

                await publish_terrain(client, camp_id, state)

        except Exception as error:
            logger.error(
                "Terrain message failed | field=%s | topic=%s | error=%s",
                camp_id,
                topic,
                error,
                exc_info=True,
            )


async def worker(
    camp_states: Dict[str, Dict[str, Any]], dedup: Deduper
) -> None:
    ssl_ctx = build_tls_context()

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_ctx,
        identifier=f"terrain-sensor-{FIELD_NAME}",
        keepalive=MQTT_KEEPALIVE,
        clean_session=False,
    )

    async with client:
        logger.info(
            "Terrain Sensor connected | field=%s | soil=%s | layout_seed=%s | broker=%s:%s",
            FIELD_NAME,
            INITIAL_SOIL_TYPE,
            SOIL_LAYOUT_SEED,
            MQTT_HOST,
            MQTT_PORT,
        )
        await listen_mqtt_telemetry(client, camp_states, dedup)


async def main() -> None:
    camp_states = {
        FIELD_NAME: create_terrain_state(
            initial_moisture=FIELD_INIT_MOIST,
            initial_oxygen=FIELD_INIT_OXY,
            soil_type=INITIAL_SOIL_TYPE,
        )
    }
    dedup = Deduper()

    while True:
        try:
            await worker(camp_states, dedup)
        except Exception as error:
            logger.error(
                "Terrain Sensor connection dropped | field=%s | error=%s | reconnecting in %ss",
                FIELD_NAME,
                error,
                MQTT_RECONNECT_SECONDS,
                exc_info=True,
            )
            await asyncio.sleep(MQTT_RECONNECT_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
