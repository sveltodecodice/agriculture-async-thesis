"""Service entry point for ambient environment telemetry and command handlers."""

import asyncio
import logging
import ssl
from typing import Dict
from datetime import datetime

import aiomqtt
from common.parameters import (
    CMD_ENV_TOPIC,
    FIELD_NAME,
    MQTT_CA_CERT,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    MQTT_RECONNECT_SECONDS,
    ENV_PUBLISH_INTERVAL_SECONDS,
    SIMULATION_START_DATE,
    TELEMETRY_ENV_TOPIC,
)
from core.manager import SensorManager
from interfaces.mqtt_client import publish_data
from utils.logger_utils import LoggingUtils

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)

_START_DATE = datetime.strptime(SIMULATION_START_DATE, "%d/%m/%Y")
START_DAY, START_MONTH, START_YEAR = _START_DATE.day, _START_DATE.month, _START_DATE.year


async def publish_loop(
    client: aiomqtt.Client, managers: Dict[str, SensorManager]
) -> None:
    """Periodically publishes environmental metrics for managed camps.

    Args:
        client (aiomqtt.Client): Connected MQTT client.
        managers (Dict[str, SensorManager]): Map of camp IDs to SensorManagers.
    """
    while True:
        for camp_id, manager in managers.items():
            state = manager.get_state()
            topic = TELEMETRY_ENV_TOPIC.format(camp_id=camp_id)
            await publish_data(client, topic, state)
            manager.update_environment()

        await asyncio.sleep(ENV_PUBLISH_INTERVAL_SECONDS)


async def listen_mqtt_commands(
    client: aiomqtt.Client, managers: Dict[str, SensorManager]
) -> None:
    """Listens for incoming admin commands to skip days or reset date states.

    Args:
        client (aiomqtt.Client): Connected MQTT client.
        managers (Dict[str, SensorManager]): Map of camp IDs to SensorManagers.
    """
    await client.subscribe(CMD_ENV_TOPIC)

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
            managers[camp_id] = SensorManager(day=START_DAY, month=START_MONTH, year=START_YEAR)

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
                telemetry_topic = TELEMETRY_ENV_TOPIC.format(camp_id=camp_id)
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
            manager.reset(day=START_DAY, month=START_MONTH, year=START_YEAR)
            logger.info(
                "[%s] Environment state reset to %s.",
                camp_id.upper(),
                SIMULATION_START_DATE,
            )
            telemetry_topic = TELEMETRY_ENV_TOPIC.format(camp_id=camp_id)
            await publish_data(client, telemetry_topic, manager.get_state())


async def worker(managers: Dict[str, SensorManager]) -> None:
    """Manages MQTT connection lifecycle and background task supervisor.

    Args:
        managers (Dict[str, SensorManager]): Map of camp IDs to SensorManagers.

    Raises:
        Exception: Propagates task exceptions to trigger connection recovery.
    """
    ssl_context = ssl.create_default_context(cafile=MQTT_CA_CERT)
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
    """Service entry point initializing default camp state and reconnection loop."""
    managers = {FIELD_NAME: SensorManager(day=START_DAY, month=START_MONTH, year=START_YEAR)}
    logger.info("Starting Ambient Sensor service")

    while True:
        try:
            await worker(managers)
        except Exception as error:
            logger.error("Connection dropped (%s). Reconnecting in %ss...", error, MQTT_RECONNECT_SECONDS)
            await asyncio.sleep(MQTT_RECONNECT_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
