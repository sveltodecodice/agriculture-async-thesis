"""Service entry point listening for MQTT plant commands and initiating seeding."""

import asyncio
import json
import logging

import aiomqtt
from common.parameters import (
    FIELD_NAME,
    HEARTBEAT_INTERVAL_SECONDS,
    HEARTBEAT_TOPIC,
    MQTT_KEEPALIVE,
    MQTT_QOS,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    MQTT_RECONNECT_SECONDS,
    PLANTATION_EVENT_SEEDED_TOPIC,
    SEEDER_CMD_PLANT_TOPIC,
)
from core.seeder import start_seeding
from utils.logger_utils import LoggingUtils
from utils.mqtt_utils import build_tls_context, publish_json

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)



async def heartbeat_loop(client: aiomqtt.Client) -> None:
    """Publish service presence for the system-status view."""
    while True:
        await publish_json(
            client,
            HEARTBEAT_TOPIC,
            {"service": "seeder", "field": FIELD_NAME, "status": "online"},
            retain=True,
        )
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


async def listen_mqtt_commands(client: aiomqtt.Client) -> None:
    """Subscribes to incoming seeder commands and publishes seeding events.

    Args:
        client (aiomqtt.Client): Active MQTT client instance.
    """
    await client.subscribe(SEEDER_CMD_PLANT_TOPIC, qos=MQTT_QOS)
    logger.info(
        "Seeder ready | field=%s | topic=%s", FIELD_NAME, SEEDER_CMD_PLANT_TOPIC
    )

    async for message in client.messages:
        topic = str(message.topic)

        try:
            raw = (
                message.payload.decode("utf-8")
                if isinstance(message.payload, bytes)
                else str(message.payload)
            )

            try:
                seed_request = json.loads(raw)
            except json.JSONDecodeError:
                seed_request = raw

            seed_data = start_seeding(seed_request)

            logger.info(
                "Seeding completed | field=%s | seed=%s",
                FIELD_NAME,
                seed_data["name"],
            )

            await publish_json(
                client,
                PLANTATION_EVENT_SEEDED_TOPIC,
                seed_data,
                qos=MQTT_QOS,
            )

        except Exception as error:
            logger.error(
                "Seeder command failed | field=%s | topic=%s | error=%s",
                FIELD_NAME,
                topic,
                error,
                exc_info=True,
            )


async def worker() -> None:
    """Manages secure MQTT connection lifecycle for the seeder task."""
    ssl_context = build_tls_context()

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_context,
        identifier=f"seeder-{FIELD_NAME}",
        keepalive=MQTT_KEEPALIVE,
        clean_session=False,
    )

    async with client:
        logger.info(
            "Seeder connected | field=%s | broker=%s:%s",
            FIELD_NAME,
            MQTT_HOST,
            MQTT_PORT,
        )
        listener_task = asyncio.create_task(listen_mqtt_commands(client))
        heartbeat_task = asyncio.create_task(heartbeat_loop(client))

        done, pending = await asyncio.wait(
            [listener_task, heartbeat_task],
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            if task.exception():
                raise task.exception()


async def main() -> None:
    """Service entry point initiating persistent reconnection loop."""
    while True:
        try:
            await worker()
        except Exception as error:
            logger.error(
                "Seeder connection dropped | field=%s | error=%s | reconnecting in %ss",
                FIELD_NAME,
                error,
                MQTT_RECONNECT_SECONDS,
                exc_info=True,
            )
            await asyncio.sleep(MQTT_RECONNECT_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
