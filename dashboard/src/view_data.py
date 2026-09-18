"""Small view-specific projections for the dashboard API.

Each page receives only the data it needs. This keeps agronomic, operational
and technical information separated without changing the underlying farm state.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from time import time
from typing import Any

from config import (
    CAMP_IDS,
    MQTT_HOST,
    MQTT_KEEPALIVE,
    MQTT_PORT,
    MQTT_QOS,
    MQTT_TLS_MIN_VERSION,
    SERVICE_HEARTBEAT_MAX_AGE_SECONDS,
)


def _base(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {"revision": snapshot.get("revision", 0)}


def overview_view(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = _base(snapshot)
    result["camps"] = {}

    for camp_id in CAMP_IDS:
        camp = snapshot.get("camps", {}).get(camp_id, {})
        terrain = camp.get("terrain", {})
        plantation = camp.get("plantation", {})
        result["camps"][camp_id] = {
            "environment": deepcopy(camp.get("environment", {})),
            "terrain": {
                "soil_moisture": terrain.get("soil_moisture"),
                "oxygenation": terrain.get("oxygenation"),
                "soil_type": terrain.get("soil_type"),
            },
            "plantation": {
                "crop": plantation.get("crop"),
                "occupied": plantation.get("occupied"),
                "time_left": plantation.get("time_left"),
                "growth_percentage": plantation.get("growth_percentage"),
                "growth_stage": plantation.get("growth_stage"),
                "health": plantation.get("health"),
                "last_status_at": plantation.get("last_status_at"),
            },
            "manager_policy": deepcopy(camp.get("manager_policy", {})),
        }

    return result


def field_view(snapshot: dict[str, Any], camp_id: str) -> dict[str, Any]:
    result = _base(snapshot)
    camp = snapshot.get("camps", {}).get(camp_id, {})
    system = camp.get("system", {})

    result["camps"] = {
        camp_id: {
            "environment": {
                key: value
                for key, value in deepcopy(camp.get("environment", {})).items()
                if key != "date"
            },
            "terrain": deepcopy(camp.get("terrain", {})),
            "plantation": deepcopy(camp.get("plantation", {})),
            "manager_policy": deepcopy(camp.get("manager_policy", {})),
            "system": {
                "actuators": {
                    "irrigator": deepcopy(
                        system.get("actuators", {}).get("irrigator", {})
                    )
                },
                "automation": deepcopy(system.get("automation", {})),
            },
        }
    }
    return result


def notifications_view(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = _base(snapshot)
    result["notifications"] = [
        {
            "message": item.get("message"),
            "camp_id": item.get("camp_id"),
            "received_at": item.get("received_at"),
        }
        for item in snapshot.get("notifications", [])
    ]
    result["activity"] = [
        {
            "date": item.get("date"),
            "event": item.get("event"),
            "details": item.get("details"),
            "camp_id": item.get("camp_id"),
        }
        for item in snapshot.get("activity", [])
    ]
    result["commands"] = [
        {
            "camp_id": item.get("camp_id"),
            "action": item.get("action"),
            "status": item.get("status"),
            "requested_at": item.get("requested_at"),
        }
        for item in snapshot.get("commands", [])
    ]
    return result


def _seconds_since_iso(value: Any) -> float | None:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - stamp).total_seconds())
    except (TypeError, ValueError):
        return None


def _heartbeat_service(value: dict[str, Any]) -> dict[str, Any]:
    observed = value.get("observed_at")
    try:
        age = max(0.0, time() - float(observed)) if observed is not None else None
    except (TypeError, ValueError):
        age = None
    if age is None:
        age = _seconds_since_iso(value.get("received_at"))

    online = (
        str(value.get("status", "")).upper() == "ONLINE"
        and age is not None
        and age <= SERVICE_HEARTBEAT_MAX_AGE_SECONDS
    )
    return {
        "status": "ONLINE" if online else "OFFLINE",
        "last_seen_seconds_ago": round(age, 1) if age is not None else None,
    }


def _irrigator_service(value: dict[str, Any]) -> dict[str, Any]:
    age = _seconds_since_iso(value.get("observed_at") or value.get("received_at"))
    if age is None:
        raw_age = value.get("last_seen_seconds_ago")
        try:
            age = float(raw_age) if raw_age is not None else None
        except (TypeError, ValueError):
            age = None

    online = (
        str(value.get("status", "")).upper() == "ONLINE"
        and age is not None
        and age <= SERVICE_HEARTBEAT_MAX_AGE_SECONDS
    )
    return {
        "status": "ONLINE" if online else "OFFLINE",
        "last_seen_seconds_ago": round(age, 1) if age is not None else None,
        "operation": value.get("operation", "unknown"),
    }


def system_status_view(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = _base(snapshot)
    mqtt = snapshot.get("mqtt", {})
    manager = snapshot.get("camp_manager", {})

    mqtt_age = _seconds_since_iso(mqtt.get("last_message_at"))
    manager_age = _seconds_since_iso(manager.get("last_heartbeat"))

    result["mqtt"] = {
        "connected": bool(mqtt.get("connected")),
        "host": MQTT_HOST,
        "port": MQTT_PORT,
        "message_count": mqtt.get("message_count", 0),
        "last_message_age_seconds": round(mqtt_age, 1) if mqtt_age is not None else None,
        "has_error": bool(mqtt.get("last_error")),
        "transport": "MQTT su TLS",
        "tls_minimum_version": MQTT_TLS_MIN_VERSION,
        "qos": MQTT_QOS,
        "keepalive_seconds": MQTT_KEEPALIVE,
    }
    result["camp_manager"] = {
        "connected": bool(manager.get("connected")),
        "status": manager.get("status", "unknown"),
        "last_seen_seconds_ago": round(manager_age, 1) if manager_age is not None else None,
    }
    result["camps"] = {}

    for camp_id in CAMP_IDS:
        system = snapshot.get("camps", {}).get(camp_id, {}).get("system", {})
        heartbeats = system.get("heartbeats", {})
        irrigator = system.get("actuators", {}).get("irrigator", {})
        result["camps"][camp_id] = {
            "services": {
                "ambient_sensor": _heartbeat_service(heartbeats.get("ambient_sensor", {})),
                "terrain_sensor": _heartbeat_service(heartbeats.get("terrain_sensor", {})),
                "plantation_sensor": _heartbeat_service(heartbeats.get("plantation_sensor", {})),
                "seeder": _heartbeat_service(heartbeats.get("seeder", {})),
                "harvester": _heartbeat_service(heartbeats.get("harvester", {})),
                "irrigator": _irrigator_service(irrigator),
            }
        }

    return result

