"""MQTT payload serialization utilities."""

import json
import time
from typing import Any, Dict


async def publish_json(
    client: Any, topic: str, payload: Dict[str, Any], **kwargs: Any
) -> None:
    """Serializes a payload dictionary to JSON with a timestamp and publishes it.

    Args:
        client (Any): Active MQTT client instance.
        topic (str): Target MQTT topic.
        payload (Dict[str, Any]): Dictionary payload to serialize.
        **kwargs: Additional keyword arguments passed to client.publish.
    """
    stamped_payload = {**payload, "ts": time.time()}
    await client.publish(topic, json.dumps(stamped_payload), **kwargs)
