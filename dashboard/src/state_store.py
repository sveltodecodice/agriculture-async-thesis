"""Small thread-safe in-memory state shared by MQTT and HTTP."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import threading
from typing import Any

from config import CAMPS, MANAGER_HEARTBEAT_MAX_AGE_SECONDS, MQTT_CLIENT_ID, MQTT_HOST, MQTT_PORT, TOPICS
from manager_logic import manager_policy


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sensor_status() -> dict[str, Any]:
    return {"status": "UNKNOWN", "last_seen_seconds_ago": None, "latency_ms": None}


def empty_camp() -> dict[str, Any]:
    return {
        "environment": {
            "date": None, "season": None, "weather": None, "temperature": None,
            "humidity_air": None, "rain_mm": None, "wind_kmh": None, "radiation_wm2": None,
        },
        "terrain": {
            "soil_moisture": None, "oxygenation": None, "soil_type": None,
            "water_dispensed_mm": None, "irrigation_active": None,
            "last_irrigation_amount_pct": None, "last_irrigation_id": None,
            "last_reoxygenation_id": None, "last_action": None,
        },
        "plantation": {
            "crop": "Nessuna", "crop_key": None, "occupied": False,
            "time_left": None, "growth_percentage": 0.0, "growth_stage": "EMPTY",
            "health": "FIELD IS EMPTY", "min_moisture": None, "max_moisture": None,
            "min_temperature": None, "max_temperature": None, "ideal_soil": None,
            "harvest_days": None, "seasons": [], "last_status_at": None,
        },
        "system": {
            "mqtt_connected": None,
            "overall_health": "UNKNOWN",
            "sensors": {
                "environment": sensor_status(),
                "terrain": sensor_status(),
                "plantation": sensor_status(),
            },
            "actuators": {
                "irrigator": {
                    "status": "UNKNOWN", "last_seen_seconds_ago": None, "latency_ms": None,
                    "operation": "unknown", "active_request_id": None,
                    "last_request_id": None, "last_action": None, "last_amount": None,
                    "last_completed_at": None,
                }
            },
            "automation": {
                "irrigation": {"pending": False, "request_id": None, "target_min_pct": None, "target_after_pct": None},
                "reoxygenation": {"pending": False, "request_id": None, "threshold_pct": 30.0},
            },
            "updated_at": None,
            "received_at": None,
        },
        "last_seen": None,
    }


class FarmState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.revision = 0
        self.camps = {camp: empty_camp() for camp in CAMPS}
        self.mqtt = {
            "connected": False,
            "host": MQTT_HOST,
            "port": MQTT_PORT,
            "client_id": MQTT_CLIENT_ID,
            "subscriptions": list(TOPICS),
            "message_count": 0,
            "topic_counts": {},
            "last_message_at": None,
            "last_topic": None,
            "last_error": None,
        }
        self.camp_manager = {"status": "unknown", "last_heartbeat": None, "camps": []}
        self.commands: list[dict[str, Any]] = []
        self.notifications: list[dict[str, Any]] = []
        self.activity: list[dict[str, Any]] = []

    def touch(self) -> None:
        self.revision += 1

    def set_mqtt(self, *, connected: bool, error: str | None = None) -> None:
        with self.lock:
            self.mqtt["connected"] = connected
            self.mqtt["last_error"] = error
            self.touch()

    def note_message(self, topic: str) -> None:
        self.mqtt["last_message_at"] = utc_now()
        self.mqtt["last_topic"] = topic
        self.mqtt["message_count"] += 1
        counts = self.mqtt["topic_counts"]
        counts[topic] = counts.get(topic, 0) + 1

    def manager_connected(self) -> bool:
        heartbeat = self.camp_manager.get("last_heartbeat")
        if not heartbeat:
            return False
        try:
            stamp = datetime.fromisoformat(str(heartbeat).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - stamp).total_seconds() <= MANAGER_HEARTBEAT_MAX_AGE_SECONDS
        except (TypeError, ValueError):
            return False

    def add_command(self, record: dict[str, Any]) -> None:
        self.commands = (self.commands + [record])[-30:]

    def add_notification(self, record: dict[str, Any]) -> None:
        self.notifications = (self.notifications + [record])[-40:]

    def set_activity(self, records: list[dict[str, Any]]) -> None:
        self.activity = records[-60:]

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            manager = deepcopy(self.camp_manager)
            manager["connected"] = self.manager_connected()
            camps = deepcopy(self.camps)
            for camp in camps.values():
                camp["manager_policy"] = manager_policy(camp)
            return {
                "revision": self.revision,
                "generated_at": utc_now(),
                "mqtt": deepcopy(self.mqtt),
                "camp_manager": manager,
                "camps": camps,
                "commands": deepcopy(self.commands),
                "notifications": deepcopy(self.notifications),
                "activity": deepcopy(self.activity),
            }


STATE = FarmState()
