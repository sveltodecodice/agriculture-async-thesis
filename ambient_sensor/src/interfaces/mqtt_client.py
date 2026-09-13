import asyncio
from typing import Any

from utils.mqtt_utils import publish_json


async def dispatch_payload(handler, raw_payload: Any) -> None:
    """
    Decodes an incoming MQTT message payload and dispatches it to a handler.

    Handles both synchronous and asynchronous callbacks transparently.

    Args:
        handler: Function or coroutine to execute with the
            decoded string payload.
        raw_payload (Any): Incoming message payload (bytes or string).
    """
    payload_text = (
        raw_payload.decode() if isinstance(raw_payload, bytes) else str(raw_payload)
    )
    handler_result = handler(payload_text)
    if asyncio.iscoroutine(handler_result):
        await handler_result


async def publish_data(client: Any, topic: str, data: dict) -> None:
    """
    Publishes a data dictionary payload to an MQTT topic with QoS 1.

    Delegates JSON formatting and timestamp attachment to mqtt_utils.publish_json.

    Args:
        client (Any): Active MQTT client instance.
        topic (str): Target MQTT topic to publish to.
        data (dict): Dictionary payload to serialize and publish.
    """
    await publish_json(client, topic, data, qos=1)


async def listen_commands(client: Any, handlers: dict) -> None:
    """
    Subscribes to command topics and dispatches incoming messages to handlers.

    Args:
        client (Any): Active MQTT client instance.
        handlers (dict): Dictionary mapping target topic
            names to their respective payload handlers.
    """
    if not handlers:
        return

    for target_topic in handlers:
        await client.subscribe(target_topic)

    async for message in client.messages:
        topic_name = str(message.topic)
        if topic_name in handlers:
            await dispatch_payload(handlers[topic_name], message.payload)
