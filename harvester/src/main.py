"""Service entry point for harvester command processing and event dispatching."""

import asyncio
import json
import logging
from time import time

import aiomqtt
from common.parameters import (
    FIELD_NAME,
    HEARTBEAT_INTERVAL_SECONDS,
    HEARTBEAT_TOPIC,
    HARVEST_CMD_TOPIC,
    HARVEST_EVENT_TOPIC,
    MQTT_KEEPALIVE,
    MQTT_QOS,
    MQTT_HOST,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_USER,
    MQTT_RECONNECT_SECONDS,
)
from core.harvester import start_harvesting
from core.harvester_deposit import save_harvest
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
            {"service": "harvester", "field": FIELD_NAME, "status": "ONLINE", "ts": time()},
            retain=True,
        )
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


async def listen_mqtt_commands(client: aiomqtt.Client) -> None:
    """Subscribes to harvest command topics and processes harvest requests.

    Args:
        client (aiomqtt.Client): Connected MQTT client instance.
    """
    await client.subscribe(HARVEST_CMD_TOPIC, qos=MQTT_QOS)
    logger.info("Harvester ready | field=%s | topic=%s", FIELD_NAME, HARVEST_CMD_TOPIC)

    async for message in client.messages:
        try:
            raw_payload = (
                message.payload.decode("utf-8")
                if isinstance(message.payload, bytes)
                else str(message.payload)
            )

            harvest_request = json.loads(raw_payload)
            harvest_data = start_harvesting(harvest_request)

            save_harvest(
                harvest_data["seed"],
                harvest_data.get("date"),
            )

            logger.info(
                "Harvest completed | field=%s | seed=%s",
                FIELD_NAME,
                harvest_data["seed"],
            )

            await publish_json(client, HARVEST_EVENT_TOPIC, harvest_data, qos=MQTT_QOS)

        except Exception as error:
            logger.error(
                "Harvester command failed | field=%s | topic=%s | error=%s",
                FIELD_NAME,
                str(message.topic),
                error,
                exc_info=True,
            )


async def worker() -> None:
    """Manages the MQTT client lifecycle and network loop.

    Raises:
        Exception: Re-raises connection exceptions to trigger reconnection in main loop.
    """
    ssl_context = build_tls_context()

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASSWORD,
        tls_context=ssl_context,
        identifier=f"harvester-{FIELD_NAME}",
        keepalive=MQTT_KEEPALIVE,
        clean_session=False,
    )

    async with client:
        logger.info(
            "Harvester connected | field=%s | broker=%s:%s",
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
    """Service entry point handling persistent connection retries."""
    while True:
        try:
            await worker()
        except Exception as error:
            logger.error(
                "Harvester connection dropped | field=%s | error=%s | reconnecting in %ss",
                FIELD_NAME,
                error,
                MQTT_RECONNECT_SECONDS,
                exc_info=True,
            )
            await asyncio.sleep(MQTT_RECONNECT_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
