"""MQTT payload serialization utilities."""

import ssl
import json
import time
from typing import Any, Dict
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
    kwargs["qos"] = MQTT_QOS
    await client.publish(topic, json.dumps(stamped_payload), **kwargs)
