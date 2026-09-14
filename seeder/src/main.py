import asyncio
import json
import logging
import ssl

import aiomqtt

from common.parameters import FIELD_NAME, MQTT_HOST, MQTT_PASS, MQTT_PORT, MQTT_USER
from core.seeder import start_seeding
from utils.logger_utils import LoggingUtils
from utils.mqtt_utils import publish_json

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)


async def listen_mqtt_commands(client: aiomqtt.Client) -> None:
    command_topic = f"camp/{FIELD_NAME}/seeder/cmd/plant"
    await client.subscribe(command_topic, qos=1)

    logger.info("Seeder ready | field=%s | topic=%s", FIELD_NAME, command_topic)

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
                f"camp/{FIELD_NAME}/plantation/event/seeded",
                seed_data,
                qos=1,
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
    ssl_context = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_context,
        identifier=f"seeder-{FIELD_NAME}",
    )

    async with client:
        logger.info(
            "Seeder connected | field=%s | broker=%s:%s",
            FIELD_NAME,
            MQTT_HOST,
            MQTT_PORT,
        )
        await listen_mqtt_commands(client)


async def main() -> None:
    while True:
        try:
            await worker()
        except Exception as error:
            logger.error(
                "Seeder connection dropped | field=%s | error=%s | reconnecting in 5s",
                FIELD_NAME,
                error,
                exc_info=True,
            )
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
