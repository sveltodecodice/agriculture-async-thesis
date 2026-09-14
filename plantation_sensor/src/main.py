import asyncio
import json
import logging
import ssl
from typing import Any, Dict

import aiomqtt
from common.constants import KNOWN_CAMPS
from common.parameters import (
    FIELD_NAME,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
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
from utils.mqtt_utils import Deduper, publish_json

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)


def create_camp_context(camp_id: str = FIELD_NAME) -> Dict[str, Any]:
    """Initializes a new context dictionary for a specific camp.

    Returns:
        Dict[str, Any]: Context object containing moisture, temperature, season,
        last recorded date, and default plantation state.
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
    """Periodically publishes plantation status and metadata for all active camps.

    Args:
        mqtt (aiomqtt.Client): Active MQTT client instance.
        camp_contexts (Dict[str, Dict[str, Any]]): Dictionary mapping camp IDs
            to their respective state context dictionaries.
    """
    while True:
        await asyncio.sleep(3)
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
            )
            await mqtt.publish(
                f"camp/{camp_id}/plantation/time_left",
                str(status_detail["time_left"]),
            )
            await mqtt.publish(
                f"camp/{camp_id}/plantation/growth_stage",
                str(status_detail["growth_stage"]),
            )
            await mqtt.publish(
                f"camp/{camp_id}/plantation/health",
                str(status_detail["health"]),
            )


async def listen_mqtt_telemetry(
    mqtt: aiomqtt.Client,
    camp_contexts: Dict[str, Dict[str, Any]],
    dedup: Deduper,
) -> None:
    """Listens for incoming MQTT telemetry and commands, updating camp states.

    Args:
        mqtt (aiomqtt.Client): Active MQTT client instance.
        camp_contexts (Dict[str, Dict[str, Any]]): Map of camp IDs to contexts.
        dedup (Deduper): Deduplication handler for filtering stale messages.
    """
    await mqtt.subscribe(f"camp/{FIELD_NAME}/terrain/telemetry")
    await mqtt.subscribe(f"camp/{FIELD_NAME}/environment/telemetry")
    await mqtt.subscribe(f"camp/{FIELD_NAME}/plantation/cmd/#")

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

        elif "plantation/cmd/" in topic:
            command = topic.split("plantation/cmd/")[-1].lower()
            if command == "plant":
                try:
                    seed_data = json.loads(payload_text)
                except Exception:
                    seed_data = {"name": payload_text.strip()}
                seed_planted(context["plantation"], seed_data)
                logger.info(
                    "[%s] Planted seed: %s",
                    camp_id.upper(),
                    seed_data.get("name"),
                )
            elif command == "clear":
                clear_field(context["plantation"])
                logger.info("[%s] Field cleared.", camp_id.upper())
            elif command in ("reset", "restart"):
                reset(context["plantation"])
                logger.info("[%s] State reset.", camp_id.upper())


async def worker(camp_contexts: Dict[str, Dict[str, Any]], dedup: Deduper) -> None:
    """Manages the MQTT connection life cycle and spawns async tasks.

    Args:
        camp_contexts (Dict[str, Dict[str, Any]]): Shared camp state map.
        dedup (Deduper): Shared deduplication instance.

    Raises:
        Exception: Re-raises exceptions encountered by background tasks to
            trigger reconnection in main loop.
    """
    ssl_context = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_context,
        identifier=f"plantation-sensor-{FIELD_NAME}",
    )
    async with client:
        logger.info("Multi-camp subsystem online.")
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
    """Service entry point initializing camp contexts and reconnection loop."""
    field_ctx = {FIELD_NAME: create_camp_context(FIELD_NAME)}
    dedup = Deduper()

    while True:
        try:
            await worker(field_ctx, dedup)
        except Exception as error:
            logger.error("Connection dropped (%s). Reconnecting in 5s...", error)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
