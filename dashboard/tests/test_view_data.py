import os
import sys
from pathlib import Path
from time import time

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

from message_handlers import handle_message
from state_store import FarmState
from view_data import field_view, notifications_view, overview_view, system_status_view


def test_overview_does_not_expose_system_or_notification_data():
    payload = overview_view(FarmState().snapshot())

    assert "mqtt" not in payload
    assert "camp_manager" not in payload
    assert "commands" not in payload
    assert "notifications" not in payload
    assert "activity" not in payload
    assert all("system" not in camp for camp in payload["camps"].values())


def test_field_view_exposes_only_requested_field_and_not_current_day():
    payload = field_view(FarmState().snapshot(), "field_a")

    assert list(payload["camps"]) == ["field_a"]
    assert "mqtt" not in payload
    assert "date" not in payload["camps"]["field_a"]["environment"]
    assert "sensors" not in payload["camps"]["field_a"]["system"]
    assert "heartbeats" not in payload["camps"]["field_a"]["system"]
    assert "automation" in payload["camps"]["field_a"]["system"]


def test_notifications_view_does_not_expose_farm_telemetry_or_system_data():
    payload = notifications_view(FarmState().snapshot())

    assert "camps" not in payload
    assert "mqtt" not in payload
    assert "camp_manager" not in payload
    assert set(payload) >= {"notifications", "activity", "commands"}


def test_heartbeat_populates_system_status_service_state():
    state = FarmState()
    handle_message(
        state,
        "camp/field_a/heartbeat/seeder",
        {"service": "seeder", "field": "field_a", "status": "online", "ts": time()},
    )

    payload = system_status_view(state.snapshot())
    assert payload["camps"]["field_a"]["services"]["seeder"]["status"] == "ONLINE"


def test_system_status_does_not_expose_credentials_topics_or_agronomic_data():
    payload = system_status_view(FarmState().snapshot())
    mqtt = payload["mqtt"]

    assert "password" not in mqtt
    assert "username" not in mqtt
    assert "subscriptions" not in mqtt
    assert "last_topic" not in mqtt
    assert "last_error" not in mqtt
    assert "last_message_at" not in mqtt
    assert mqtt["qos"] == 2

    field = payload["camps"]["field_a"]
    assert "environment" not in field
    assert "terrain" not in field
    assert "plantation" not in field
    assert set(field["services"]) == {
        "ambient_sensor",
        "terrain_sensor",
        "plantation_sensor",
        "irrigator",
        "seeder",
        "harvester",
    }
