"""Service entry point for irrigator commands and event dispatching."""

import asyncio
import json
import logging
import ssl

import aiomqtt
from common.parameters import (
    FIELD_NAME,
    IRRIGATE_CMD_TOPIC,
    IRRIGATED_EVENT_TOPIC,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    REOXYGENATE_CMD_TOPIC,
    REOXYGENATED_EVENT_TOPIC,
)
from core.irrigator import start_irrigation, start_reoxygenation
from utils.logger_utils import LoggingUtils
from utils.mqtt_utils import publish_json

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)


async def listen_mqtt_commands(client: aiomqtt.Client) -> None:
    """Subscribes to irrigation and reoxygenation command topics.

    Args:
        client (aiomqtt.Client): Connected MQTT client instance.
    """
    await client.subscribe(IRRIGATE_CMD_TOPIC, qos=1)
    await client.subscribe(REOXYGENATE_CMD_TOPIC, qos=1)

    logger.info(
        "Irrigator ready | field=%s | irrigation=%s | oxygenation=%s",
        FIELD_NAME,
        IRRIGATE_CMD_TOPIC,
        REOXYGENATE_CMD_TOPIC,
    )

    async for message in client.messages:
        topic = str(message.topic)

        try:
            raw_payload = (
                message.payload.decode("utf-8")
                if isinstance(message.payload, bytes)
                else str(message.payload)
            )

            command = topic.rsplit("/", 1)[-1].lower()

            if command == "irrigate":
                try:
                    request = json.loads(raw_payload)
                except json.JSONDecodeError:
                    request = raw_payload

                result = start_irrigation(request)

                logger.info(
                    "Irrigation completed | field=%s | amount=%.1f",
                    FIELD_NAME,
                    result["amount"],
                )

                await publish_json(client, IRRIGATED_EVENT_TOPIC, result, qos=1)

            elif command == "reoxygenate":
                result = start_reoxygenation()

                logger.info(
                    "Reoxygenation completed | field=%s | oxygenation=%.1f",
                    FIELD_NAME,
                    result["oxygenation"],
                )

                await publish_json(client, REOXYGENATED_EVENT_TOPIC, result, qos=1)

        except Exception as error:
            logger.error(
                "Irrigator command failed | field=%s | topic=%s | error=%s",
                FIELD_NAME,
                topic,
                error,
                exc_info=True,
            )


async def worker() -> None:
    """Manages the MQTT client lifecycle and network loop.

    Raises:
        Exception: Re-raises connection exceptions to trigger reconnection in main loop.
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
        identifier=f"irrigator-{FIELD_NAME}",
    )

    async with client:
        logger.info(
            "Irrigator connected | field=%s | broker=%s:%s",
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
                "Irrigator connection dropped | field=%s | error=%s | reconnecting in 5s",
                FIELD_NAME,
                error,
                exc_info=True,
            )
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
