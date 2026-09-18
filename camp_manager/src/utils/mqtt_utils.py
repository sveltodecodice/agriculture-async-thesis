"""MQTT payload serialization and message deduplication utilities."""

import ssl
import json
import time
from typing import Any, Dict, Optional
from common.parameters import MQTT_CA_CERT, MQTT_QOS, MQTT_TLS_MIN_VERSION



def build_tls_context() -> ssl.SSLContext:
    """Build a verified TLS context for every MQTT connection/reconnection."""
    versions = {
        "TLSv1.2": ssl.TLSVersion.TLSv1_2,
        "TLSv1.3": ssl.TLSVersion.TLSv1_3,
    }
    minimum = versions.get(MQTT_TLS_MIN_VERSION)
    if minimum is None:
        raise ValueError(f"Unsupported MQTT TLS minimum version: {MQTT_TLS_MIN_VERSION}")

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=MQTT_CA_CERT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.minimum_version = minimum
    return context

class Deduper:
    """Tracks message timestamps per topic to detect duplicate or stale data."""

    def __init__(self) -> None:
        """Initializes an empty timestamp tracking dictionary."""
        self._last_seen: Dict[str, float] = {}

    def is_duplicate_or_stale(self, topic: str, timestamp: Any) -> bool:
        """Determines if a message is duplicate or stale based on its timestamp.

        Args:
            topic (str): The MQTT topic associated with the message.
            timestamp (Any): Payload timestamp to validate.

        Returns:
            bool: True if the timestamp is less than or equal to the last recorded timestamp.
        """
        try:
            numeric_ts = float(timestamp)
        except (TypeError, ValueError):
            return False

        previous_timestamp = self._last_seen.get(topic)
        if previous_timestamp is not None and numeric_ts <= previous_timestamp:
            return True

        self._last_seen[topic] = numeric_ts
        return False

    def reset(self, topic: Optional[str] = None) -> None:
        """Resets tracked timestamps for a specific topic or all topics.

        Args:
            topic (Optional[str]): Target MQTT topic to clear. Clears all if None.
        """
        if topic is None:
            self._last_seen.clear()
        else:
            self._last_seen.pop(topic, None)


async def publish_json(
    client: Any, topic: str, payload: Dict[str, Any], **kwargs: Any
) -> None:
    """Publishes a dictionary payload as JSON with an attached wall-clock timestamp.

    Args:
        client (Any): Active MQTT client instance.
        topic (str): Target MQTT topic.
        payload (Dict[str, Any]): Dictionary payload to serialize.
        **kwargs: Keyword arguments passed to client.publish.
    """
    stamped_payload = {**payload, "ts": time.time()}
    kwargs["qos"] = MQTT_QOS
    await client.publish(topic, json.dumps(stamped_payload), **kwargs)
