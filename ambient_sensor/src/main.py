import asyncio
import logging
import ssl

import aiomqtt
from common.parameters import (
    FIELD_NAME,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
)
from core.manager import SensorManager
from interfaces.mqtt_client import publish_data
from utils.logger_utils import LoggingUtils

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)


async def publish_loop(client: aiomqtt.Client, managers: dict) -> None:
    """Periodically publishes environmental state metrics for all active camps.

    Args:
        client (aiomqtt.Client): Active MQTT client instance.
        managers (dict): Dictionary mapping camp IDs to
            their respective SensorManager instances.
    """
    while True:
        for camp_id, manager in managers.items():
            state = manager.get_state()
            topic = f"camp/{camp_id}/environment/telemetry"
            await publish_data(client, topic, state)
            manager.update_environment()

        await asyncio.sleep(10)


async def listen_mqtt_commands(client: aiomqtt.Client, managers: dict) -> None:
    """Listens for administrative commands on environment MQTT command topics.

    Supported commands:
        - .../cmd/skip: Advances environmental state by N days (default 1).
        - .../cmd/reset: Resets environmental state back to 01/01/2026.

    Args:
        client (aiomqtt.Client): Active MQTT client instance.
        managers (dict): Dictionary mapping camp IDs to
            their respective SensorManager instances.
    """
    await client.subscribe(f"camp/{FIELD_NAME}/environment/cmd/#")

    async for message in client.messages:
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

        if camp_id not in managers:
            managers[camp_id] = SensorManager(day=1, month=1, year=2026)

        manager = managers[camp_id]

        if topic.endswith("/skip"):
            try:
                days = int(payload_text.strip())
            except ValueError:
                days = 1

            current_state = manager.get_state()
            for _ in range(days):
                manager.update_environment()
                current_state = manager.get_state()
                telemetry_topic = f"camp/{camp_id}/environment/telemetry"
                await publish_data(client, telemetry_topic, current_state)
                await asyncio.sleep(0.1)

            logger.info(
                "[%s] Skipped %d days. Current date: %02d/%02d/%d",
                camp_id.upper(),
                days,
                current_state["day"],
                current_state["month"],
                current_state["year"],
            )

        elif topic.endswith("/reset"):
            manager._create_timer_state(day=1, month=1, year=2026)
            logger.info(
                "[%s] Environment state reset to 01/01/2026.",
                camp_id.upper(),
            )
            telemetry_topic = f"camp/{camp_id}/environment/telemetry"
            await publish_data(client, telemetry_topic, manager.get_state())


async def worker(managers: dict) -> None:
    """Manages the MQTT connection lifecycle and supervises background tasks.

    Args:
        managers (dict): Map of camp IDs to SensorManager
            instances.

    Raises:
        Exception: Re-raises exceptions caught from background tasks to signal
            reconnection handling in the main loop.
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
        identifier=f"ambient-sensor-{FIELD_NAME}",
    )
    async with client:
        logger.info("Multi-camp service online. Starting tasks...")

        publish_task = asyncio.create_task(publish_loop(client, managers))
        listener_task = asyncio.create_task(listen_mqtt_commands(client, managers))

        done, pending = await asyncio.wait(
            [publish_task, listener_task], return_when=asyncio.FIRST_EXCEPTION
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
    """Service entry point initializing camp managers and handling reconnects."""
    managers = {FIELD_NAME: SensorManager(day=1, month=1, year=2026)}
    logger.info("Starting Ambient Sensor")

    while True:
        try:
            await worker(managers)
        except Exception as error:
            logger.error("Connection dropped (%s). Reconnecting in 5s...", error)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
