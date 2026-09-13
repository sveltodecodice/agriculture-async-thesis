import json
import time
from typing import Any, Optional


class Deduper:
    """Tracks message timestamps per topic to detect duplicate or stale data.

    Each service requiring deduplication must maintain its own instance of this
    class to preserve independent topic state tracking.
    """

    def __init__(self) -> None:
        """Initializes an empty timestamp tracking dictionary."""
        self._last_seen: dict = {}

    def is_duplicate_or_stale(self, topic: str, timestamp: Any) -> bool:
        """Determines if a message is duplicate or stale based on its timestamp.

        Args:
            topic (str): The MQTT topic associated with the message.
            timestamp (Any): The payload timestamp to validate. Must be
                convertible to a float value.

        Returns:
            bool: True if the message timestamp is less than or equal to the
                last processed timestamp for the topic. If timestamp parsing
                fails, returns False (fail-open) without tracking state.
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
            topic (Optional[str], optional): Target MQTT topic to clear from
                tracking. If None, clears history for all topics. Defaults to None.
        """
        if topic is None:
            self._last_seen.clear()
        else:
            self._last_seen.pop(topic, None)


async def publish_json(client: Any, topic: str, payload: dict, **kwargs: Any) -> None:
    """Publishes a dictionary payload as a JSON string with an attached timestamp.

    Appends a wall-clock timestamp ("ts") using time.time() before serialization.

    Args:
        client (Any): The asynchronous MQTT client instance executing publish.
        topic (str): The MQTT topic to publish to.
        payload (dict): Dictionary payload to serialize and send.
        **kwargs (Any): Additional keyword arguments forwarded to client.publish.
    """
    stamped_payload = {**payload, "ts": time.time()}
    await client.publish(topic, json.dumps(stamped_payload), **kwargs)
