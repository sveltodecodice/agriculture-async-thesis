"""Service entry point for plantation status monitoring and telemetry processing."""

import asyncio
import json
import logging
from typing import Any, Dict

import aiomqtt
from common.parameters import (
    ENV_TELEMETRY_TOPIC,
    FIELD_NAME,
    MQTT_KEEPALIVE,
    MQTT_QOS,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    MQTT_RECONNECT_SECONDS,
    PLANTATION_PUBLISH_INTERVAL_SECONDS,
    PLANTATION_EVENT_TOPIC,
    TERRAIN_TELEMETRY_TOPIC,
)
from core.plant_conditions import (
    advance_days,
    clear_field,
    create_default_plantation_state,
    get_status,
    reset,
    seed_planted,
)
from utils.logger_utils import LoggingUtils
from utils.mqtt_utils import Deduper, build_tls_context, publish_json

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)


def create_camp_context(camp_id: str = FIELD_NAME) -> Dict[str, Any]:
    """Initializes context dictionary for a target camp.

    Args:
        camp_id (str): Target camp identifier.

    Returns:
        Dict[str, Any]: Initialized context map.
    """
    return {
        "camp_id": camp_id,
        "moisture": None,
        "temperature": None,
        "season": None,
        "last_date": None,
        "plantation": create_default_plantation_state(),
    }


async def monitor_loop(
    mqtt: aiomqtt.Client, camp_contexts: Dict[str, Dict[str, Any]]
) -> None:
    """Periodically publishes plantation status and metadata for active camps.

    Args:
        mqtt (aiomqtt.Client): Active MQTT client instance.
        camp_contexts (Dict[str, Dict[str, Any]]): Map of camp IDs to states.
    """
    while True:
        await asyncio.sleep(PLANTATION_PUBLISH_INTERVAL_SECONDS)
        for camp_id, context in camp_contexts.items():
            status = get_status(
                context["plantation"],
                context["moisture"],
                context["temperature"],
                context["season"],
            )
            status_topic = f"camp/{camp_id}/plantation/status"
            await publish_json(mqtt, status_topic, status)

            status_detail = status["status_detail"]
            await mqtt.publish(
                f"camp/{camp_id}/plantation/plant_name",
                str(status_detail["plant_name"]),
                qos=MQTT_QOS,
            )
            await mqtt.publish(
                f"camp/{camp_id}/plantation/time_left",
                str(status_detail["time_left"]),
                qos=MQTT_QOS,
            )
            await mqtt.publish(
                f"camp/{camp_id}/plantation/growth_stage",
                str(status_detail["growth_stage"]),
                qos=MQTT_QOS,
            )
            await mqtt.publish(
                f"camp/{camp_id}/plantation/health",
                str(status_detail["health"]),
                qos=MQTT_QOS,
            )


async def listen_mqtt_telemetry(
    mqtt: aiomqtt.Client,
    camp_contexts: Dict[str, Dict[str, Any]],
    dedup: Deduper,
) -> None:
    """Subscribes to telemetry topics and events, updating camp states.

    Args:
        mqtt (aiomqtt.Client): Active MQTT client instance.
        camp_contexts (Dict[str, Dict[str, Any]]): Shared map of camp states.
        dedup (Deduper): Deduplication handler instance.
    """
    await mqtt.subscribe(TERRAIN_TELEMETRY_TOPIC, qos=MQTT_QOS)
    await mqtt.subscribe(ENV_TELEMETRY_TOPIC, qos=MQTT_QOS)
    await mqtt.subscribe(PLANTATION_EVENT_TOPIC, qos=MQTT_QOS)

    async for message in mqtt.messages:
        topic = str(message.topic)
        payload_text = (
            message.payload.decode("utf-8")
            if isinstance(message.payload, bytes)
            else str(message.payload)
        )

        topic_parts = topic.split("/")
        if len(topic_parts) >= 2 and topic_parts[0] == "camp":
            camp_id = topic_parts[1]
        else:
            continue

        if camp_id not in camp_contexts:
            camp_contexts[camp_id] = create_camp_context(camp_id)

        context = camp_contexts[camp_id]

        if "terrain/telemetry" in topic:
            payload_data = json.loads(payload_text)
            if dedup.is_duplicate_or_stale(topic, payload_data.get("ts")):
                continue
            if "soil_moisture" in payload_data:
                context["moisture"] = float(payload_data["soil_moisture"])

        elif "environment/telemetry" in topic:
            payload_data = json.loads(payload_text)
            if dedup.is_duplicate_or_stale(topic, payload_data.get("ts")):
                continue

            if "temperature" in payload_data:
                context["temperature"] = float(payload_data["temperature"])
            if "season" in payload_data:
                context["season"] = str(payload_data["season"])

            new_date = payload_data.get("date")
            if new_date and new_date != context.get("last_date"):
                context["last_date"] = new_date
                advance_days(context["plantation"], 1)

        elif "plantation/event/" in topic:
            event = topic.split("plantation/event/")[-1].lower()

            if event == "seeded":
                seed_data = json.loads(payload_text)
                seed_planted(context["plantation"], seed_data)
                logger.info(
                    "[%s] Observed seeded event: %s",
                    camp_id.upper(),
                    seed_data.get("name"),
                )

            elif event == "harvested":
                clear_field(context["plantation"])
                logger.info("[%s] Observed harvested event.", camp_id.upper())

            elif event == "cleared":
                clear_field(context["plantation"])
                logger.info("[%s] Observed field cleared event.", camp_id.upper())

            elif event == "reset":
                reset(context["plantation"])
                logger.info("[%s] Observed plantation reset event.", camp_id.upper())


async def worker(camp_contexts: Dict[str, Dict[str, Any]], dedup: Deduper) -> None:
    """Manages MQTT connection lifecycle and background execution tasks.

    Args:
        camp_contexts (Dict[str, Dict[str, Any]]): Map of camp states.
        dedup (Deduper): Shared deduplication tracker.

    Raises:
        Exception: Re-raises task failure to initiate reconnect.
    """
    ssl_context = build_tls_context()

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_context,
        identifier=f"plantation-sensor-{FIELD_NAME}",
        keepalive=MQTT_KEEPALIVE,
        clean_session=False,
    )
    async with client:
        logger.info("Plantation sensor online | field=%s", FIELD_NAME)
        monitor_task = asyncio.create_task(monitor_loop(client, camp_contexts))
        listener_task = asyncio.create_task(
            listen_mqtt_telemetry(client, camp_contexts, dedup)
        )

        done, pending = await asyncio.wait(
            [monitor_task, listener_task], return_when=asyncio.FIRST_EXCEPTION
        )

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                logger.error(task.exception())
                raise task.exception()


async def main() -> None:
    """Service entry point initiating persistent reconnection loop."""
    field_ctx = {FIELD_NAME: create_camp_context(FIELD_NAME)}
    dedup = Deduper()

    while True:
        try:
            await worker(field_ctx, dedup)
        except Exception as error:
            logger.error("Connection dropped (%s). Reconnecting in %ss...", error, MQTT_RECONNECT_SECONDS)
            await asyncio.sleep(MQTT_RECONNECT_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
