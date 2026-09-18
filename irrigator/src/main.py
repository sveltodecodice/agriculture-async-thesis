"""Irrigator actuator: executes irrigation and reoxygenation requests."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

import aiomqtt
from common.parameters import (
    IRRIGATOR_ACTION_DELAY_SECONDS,
    FIELD_NAME,
    IRRIGATE_CMD_TOPIC,
    IRRIGATED_EVENT_TOPIC,
    IRRIGATOR_STATUS_TOPIC,
    MQTT_KEEPALIVE,
    MQTT_QOS,
    MQTT_HOST,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_USER,
    MQTT_RECONNECT_SECONDS,
    IRRIGATOR_REOXYGENATION_TARGET,
    REOXYGENATE_CMD_TOPIC,
    REOXYGENATED_EVENT_TOPIC,
    IRRIGATOR_STATUS_INTERVAL_SECONDS,
)
from core.irrigator import start_irrigation, start_reoxygenation
from utils.logger_utils import LoggingUtils
from utils.mqtt_utils import build_tls_context, publish_json

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_status() -> Dict[str, Any]:
    return {
        "service": "irrigator",
        "field": FIELD_NAME,
        "status": "ONLINE",
        "operation": "idle",
        "active_request_id": None,
        "last_request_id": None,
        "last_action": None,
        "last_amount": None,
        "last_completed_at": None,
    }


async def publish_status(
    client: aiomqtt.Client,
    status: Dict[str, Any],
) -> None:
    payload = dict(status)
    payload["observed_at"] = utc_now()
    await publish_json(
        client,
        IRRIGATOR_STATUS_TOPIC,
        payload,
        qos=MQTT_QOS,
        retain=True,
    )


async def status_loop(
    client: aiomqtt.Client,
    status: Dict[str, Any],
) -> None:
    while True:
        await publish_status(client, status)
        await asyncio.sleep(IRRIGATOR_STATUS_INTERVAL_SECONDS)


async def listen_mqtt_commands(
    client: aiomqtt.Client,
    status: Dict[str, Any],
) -> None:
    await client.subscribe(IRRIGATE_CMD_TOPIC, qos=MQTT_QOS)
    await client.subscribe(REOXYGENATE_CMD_TOPIC, qos=MQTT_QOS)

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

            try:
                request = json.loads(raw_payload)
            except json.JSONDecodeError:
                request = raw_payload

            command = topic.rsplit("/", 1)[-1].lower()
            request_id = (
                request.get("request_id")
                if isinstance(request, dict)
                else None
            )

            status["operation"] = (
                "irrigating" if command == "irrigate" else "reoxygenating"
            )
            status["active_request_id"] = request_id
            await publish_status(client, status)

            # A very small delay makes actuator state observable in the
            # dashboard without introducing complex actuator simulation.
            if IRRIGATOR_ACTION_DELAY_SECONDS > 0:
                await asyncio.sleep(IRRIGATOR_ACTION_DELAY_SECONDS)

            if command == "irrigate":
                result = start_irrigation(request)
                result["request_id"] = request_id

                await publish_json(
                    client,
                    IRRIGATED_EVENT_TOPIC,
                    result,
                    qos=MQTT_QOS,
                )

                status["last_amount"] = result["amount_pct"]
                status["last_action"] = "irrigated"

                logger.info(
                    "Irrigation completed | field=%s | request=%s | amount=%.1f",
                    FIELD_NAME,
                    request_id,
                    result["amount_pct"],
                )

            elif command == "reoxygenate":
                result = start_reoxygenation(IRRIGATOR_REOXYGENATION_TARGET)
                result["request_id"] = request_id

                await publish_json(
                    client,
                    REOXYGENATED_EVENT_TOPIC,
                    result,
                    qos=MQTT_QOS,
                )

                status["last_action"] = "reoxygenated"

                logger.info(
                    "Reoxygenation completed | field=%s | request=%s | oxygenation=%.1f",
                    FIELD_NAME,
                    request_id,
                    result["oxygenation"],
                )

            else:
                logger.warning("Unknown Irrigator command: %s", command)
                continue

            status["last_request_id"] = request_id
            status["last_completed_at"] = utc_now()
            status["active_request_id"] = None
            status["operation"] = "idle"
            await publish_status(client, status)

        except Exception as error:
            status["operation"] = "idle"
            status["active_request_id"] = None
            await publish_status(client, status)
            logger.error(
                "Irrigator command failed | field=%s | topic=%s | error=%s",
                FIELD_NAME,
                topic,
                error,
                exc_info=True,
            )


async def worker() -> None:
    ssl_context = build_tls_context()

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASSWORD,
        tls_context=ssl_context,
        identifier=f"irrigator-{FIELD_NAME}",
        keepalive=MQTT_KEEPALIVE,
        clean_session=False,
    )

    status = create_status()

    async with client:
        logger.info(
            "Irrigator connected | field=%s | broker=%s:%s",
            FIELD_NAME,
            MQTT_HOST,
            MQTT_PORT,
        )
        await publish_status(client, status)

        tasks = [
            asyncio.create_task(listen_mqtt_commands(client, status)),
            asyncio.create_task(status_loop(client, status)),
        ]

        done, pending = await asyncio.wait(
            tasks,
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
    while True:
        try:
            await worker()
        except Exception as error:
            logger.error(
                "Irrigator connection dropped | field=%s | error=%s | reconnecting in %ss",
                FIELD_NAME,
                error,
                MQTT_RECONNECT_SECONDS,
                exc_info=True,
            )
            await asyncio.sleep(MQTT_RECONNECT_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
