import asyncio
import json
import logging
import ssl
import aiomqtt

from common.parameters import (
    FIELD_INIT_MOIST,
    FIELD_INIT_OXY,
    FIELD_INIT_TYPE,
    FIELD_NAME,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
)
from utils.logger_utils import LoggingUtils
from utils.mqtt_utils import Deduper, publish_json
from core.terrain_condition import create_terrain_state, process_terrain_update

LoggingUtils.configure(
    console_level=logging.INFO,
)

logger = LoggingUtils.get_logger(__name__)


async def listen_mqtt_telemetry(client, camp_states, dedup):
    await client.subscribe(f"camp/{FIELD_NAME}/environment/telemetry")
    await client.subscribe(f"camp/{FIELD_NAME}/terrain/event/#")
    await client.subscribe(f"camp/{FIELD_NAME}/terrain/cmd/#")

    async for msg in client.messages:
        top = str(msg.topic)
        raw = (
            msg.payload.decode("utf-8")
            if isinstance(msg.payload, bytes)
            else str(msg.payload)
        )

        parts = top.split("/")
        if len(parts) >= 2 and parts[0] == "camp":
            camp_id = parts[1]
        else:
            continue

        if camp_id not in camp_states:
            raise ValueError(f"Invalid ID {camp_id}")

        state = camp_states[camp_id]

        if "environment/telemetry" in top:
            logger.debug("Fetched telemetry")
            ambient_data = json.loads(raw)
            if dedup.is_duplicate_or_stale(top, ambient_data.get("ts")):
                continue

            telemetry = process_terrain_update(state, ambient_data)
            out_topic = f"camp/{camp_id}/terrain/telemetry"

            await publish_json(client, out_topic, telemetry, qos=1)
            logger.info(
                f"[{camp_id.upper()}] [{telemetry['date']}] Soil: {telemetry.get('soil_type', 'Franco')} | "
                f"Moisture: {telemetry['soil_moisture']:.1f}% | O2: {telemetry['oxygenation']:.1f}% | "
                f"Pump: {telemetry['irrigation_active']}",
            )

        elif "terrain/event/" in top:
            event = top.split("terrain/event/")[-1].lower()
            event_data = json.loads(raw) if raw else {}

            if event == "irrigated":
                amount = float(event_data.get("amount", 15.0))
                state["soil_moisture"] = min(100.0, state["soil_moisture"] + amount)
                state["water_dispensed_mm"] = amount
                state["irrigation_active"] = False
                logger.info(
                    f"[{camp_id.upper()}] Observed irrigation (+{amount:.1f}%). New moisture: {state['soil_moisture']:.1f}%.",
                )

            elif event == "reoxygenated":
                state["oxygenation"] = float(event_data.get("oxygenation", 100.0))
                logger.info(
                    f"[{camp_id.upper()}] Observed soil reoxygenation to {state['oxygenation']:.1f}%.",
                )
            else:
                continue

            telemetry = {
                "soil_moisture": state["soil_moisture"],
                "oxygenation": state["oxygenation"],
                "soil_type": state.get("soil_type", "Franco"),
                "irrigation_active": state["irrigation_active"],
                "water_dispensed_mm": state.get("water_dispensed_mm", 0.0),
                "date": state.get("date", "01/01/2026"),
            }
            out_topic = f"camp/{camp_id}/terrain/telemetry"
            await publish_json(client, out_topic, telemetry, qos=1)

        elif "terrain/cmd/" in top:
            cmd = top.split("terrain/cmd/")[-1].lower()

            if cmd in ("set_soil_type", "set_type"):
                state["soil_type"] = raw.strip()
                logger.info(
                    f"[{camp_id.upper()}] Soil type set to: {state['soil_type']}",
                )

            elif cmd in ("reset", "restart"):
                state["soil_moisture"] = 28.0
                state["oxygenation"] = 70.0
                state["soil_type"] = "Franco"
                state["irrigation_active"] = False
                dedup.reset()
                logger.info(
                    f"[{camp_id.upper()}] Terrain state reset to 28.0%.",
                )

            telemetry = {
                "soil_moisture": state["soil_moisture"],
                "oxygenation": state["oxygenation"],
                "soil_type": state.get("soil_type", "Franco"),
                "irrigation_active": state["irrigation_active"],
                "date": state.get("date", "01/01/2026"),
            }
            out_topic = f"camp/{camp_id}/terrain/telemetry"
            await publish_json(client, out_topic, telemetry, qos=1)


async def worker(camp_states, dedup):
    ssl_ctx = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_ctx,
        identifier=f"terrain-sensor-{FIELD_NAME}",
    )
    async with client:
        logger.info("Multi-camp service online. Starting tasks...")

        t1 = asyncio.create_task(listen_mqtt_telemetry(client, camp_states, dedup))

        done, pending = await asyncio.wait([t1], return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                logger.error(task.exception())
                raise task.exception()


async def main():

    init_configuration = create_terrain_state(
        initial_moisture=FIELD_INIT_MOIST,
        initial_oxygen=FIELD_INIT_OXY,
        soil_type=FIELD_INIT_TYPE,
    )
    camp_states = {FIELD_NAME: init_configuration}
    dedup = Deduper()

    while True:
        try:
            await worker(camp_states, dedup)
        except Exception as err:
            logger.error(
                f"Connection dropped ({err}). Reconnecting in 5s...", stack_info=True
            )
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
