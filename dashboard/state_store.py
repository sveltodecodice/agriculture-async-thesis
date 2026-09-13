"""Thread-safe in-memory application state.

The MQTT thread writes here; HTTP requests read snapshots from here. Keeping this
logic isolated makes concurrency easier to understand and test.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import threading
from typing import Any

from config import CAMPS, MANAGER_HEARTBEAT_MAX_AGE_SECONDS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_sensor_status() -> dict[str, Any]:
    return {"status": "UNKNOWN", "last_seen_seconds_ago": None, "latency_ms": None}


def empty_camp() -> dict[str, Any]:
    return {
        "environment": {
            "date": None,
            "season": None,
            "weather": None,
            "temperature": None,
            "humidity_air": None,
            "rain_mm": None,
            "wind_kmh": None,
            "radiation_wm2": None,
        },
        "terrain": {
            "soil_moisture": None,
            "oxygenation": None,
            "soil_type": None,
            "water_dispensed_mm": None,
            "irrigation_active": None,
        },
        "plantation": {
            "crop": "Nessuna",
            "crop_key": None,
            "occupied": False,
            "time_left": None,
            "growth_percentage": 0.0,
            "growth_stage": "EMPTY",
            "health": "FIELD IS EMPTY",
            "min_moisture": None,
            "max_moisture": None,
            "min_temperature": None,
            "max_temperature": None,
            "ideal_soil": None,
            "harvest_days": None,
            "seasons": [],
            "last_status_at": None,
        },
        "system": {
            "mqtt_connected": None,
            "overall_health": "UNKNOWN",
            "sensors": {
                "environment": empty_sensor_status(),
                "terrain": empty_sensor_status(),
                "plantation": empty_sensor_status(),
            },
            "updated_at": None,
            "received_at": None,
        },
        "last_seen": None,
    }


class FarmState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.revision = 0
        self.camps = {camp: empty_camp() for camp in CAMPS}
        self.mqtt = {"connected": False, "last_message_at": None, "last_topic": None, "last_error": None}
        self.camp_manager = {"status": "unknown", "last_heartbeat": None, "camps": []}
        self.commands: list[dict[str, Any]] = []

    def touch(self) -> None:
        self.revision += 1
        self.changed.notify_all()

    def set_mqtt(self, *, connected: bool, error: str | None = None) -> None:
        with self.lock:
            self.mqtt["connected"] = connected
            self.mqtt["last_error"] = error
            self.touch()

    def note_message(self, topic: str) -> None:
        self.mqtt["last_message_at"] = utc_now()
        self.mqtt["last_topic"] = topic

    def manager_connected(self) -> bool:
        heartbeat = self.camp_manager.get("last_heartbeat")
        if not heartbeat:
            return False
        try:
            stamp = datetime.fromisoformat(str(heartbeat).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - stamp).total_seconds()
            return age <= MANAGER_HEARTBEAT_MAX_AGE_SECONDS
        except (TypeError, ValueError):
            return False

    def add_command(self, record: dict[str, Any]) -> None:
        self.commands.append(record)
        self.commands = self.commands[-30:]

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            manager = deepcopy(self.camp_manager)
            manager["connected"] = self.manager_connected()
            return {
                "revision": self.revision,
                "generated_at": utc_now(),
                "mqtt": deepcopy(self.mqtt),
                "camp_manager": manager,
                "camps": deepcopy(self.camps),
                "commands": deepcopy(self.commands),
            }


STATE = FarmState()
