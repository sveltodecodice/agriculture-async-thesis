import time
import json


class Deduper:
    def __init__(self):
        self._last_seen: dict[str, float] = {}

    def is_duplicate_or_stale(self, topic: str, ts) -> bool:
        try:
            ts = float(ts)
        except (TypeError, ValueError):
            return False

        prev = self._last_seen.get(topic)
        if prev is not None and ts <= prev:
            return True
        self._last_seen[topic] = ts
        return False

    def reset(self, topic: str | None = None):
        if topic is None:
            self._last_seen.clear()
        else:
            self._last_seen.pop(topic, None)


async def publish_json(client, topic, payload: dict, **kwargs):
    stamped = {**payload, "ts": time.time()}
    await client.publish(topic, json.dumps(stamped), **kwargs)