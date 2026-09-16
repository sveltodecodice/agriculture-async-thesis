"""Interface wrappers for MQTT publishing."""

from typing import Any, Dict

from utils.mqtt_utils import publish_json


async def publish_data(client: Any, topic: str, data: Dict[str, Any]) -> None:
    """Publishes telemetry data to an MQTT topic with QoS 1.

    Args:
        client (Any): Active MQTT client instance.
        topic (str): Target MQTT topic.
        data (Dict[str, Any]): Data dictionary to publish.
    """
    await publish_json(client, topic, data, qos=1)
