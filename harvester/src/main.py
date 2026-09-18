"""Service entry point for harvester command processing and event dispatching."""

import asyncio
import json
import logging
import ssl

import aiomqtt
from common.parameters import (
    FIELD_NAME,
    HARVEST_CMD_TOPIC,
    HARVEST_DEPOSIT_TOPIC,
    HARVEST_EVENT_TOPIC,
    MQTT_CA_CERT,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    MQTT_RECONNECT_SECONDS,
)
from core.harvester import start_harvesting
from core.harvester_deposit import save_harvest
from utils.logger_utils import LoggingUtils
from utils.mqtt_utils import publish_json

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)


async def listen_mqtt_commands(client: aiomqtt.Client) -> None:
    """Subscribes to harvest command topics and processes harvest requests.

    Args:
        client (aiomqtt.Client): Connected MQTT client instance.
    """
    await client.subscribe(HARVEST_CMD_TOPIC, qos=1)
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

            history = save_harvest(
                harvest_data["seed"],
                harvest_data.get("date"),
            )

            await publish_json(
                client, HARVEST_DEPOSIT_TOPIC, {"history": history}, qos=1
            )

            logger.info(
                "Harvest completed | field=%s | seed=%s",
                FIELD_NAME,
                harvest_data["seed"],
            )

            await publish_json(client, HARVEST_EVENT_TOPIC, harvest_data, qos=1)

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
    ssl_context = ssl.create_default_context(cafile=MQTT_CA_CERT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_context,
        identifier=f"harvester-{FIELD_NAME}",
    )

    async with client:
        logger.info(
            "Harvester connected | field=%s | broker=%s:%s",
            FIELD_NAME,
            MQTT_HOST,
            MQTT_PORT,
        )
        await listen_mqtt_commands(client)


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
