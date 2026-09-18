"""Functions that apply MQTT messages to FarmState."""
from __future__ import annotations

import re
from typing import Any

from normalizers import (
    bool_value,
    camp_from_topic,
    moisture_fraction,
    normalize_dict,
    plantation_from_payload,
)
from state_store import FarmState, utc_now


def _camp_from_text(state: FarmState, text: str) -> str | None:
    match = re.search(r"\[([^\]]+)\]", text or "")
    if not match:
        return None
    candidate = match.group(1).strip().lower()
    return candidate if candidate in state.camps else None


def _activity_records(state: FarmState, payload: Any) -> list[dict[str, Any]]:
    values = payload if isinstance(payload, list) else [payload]
    result: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        details = str(item.get("details", ""))
        camp_id = _camp_from_text(state, details)
        # Ignore stale history referring to a topology that is no longer configured.
        if re.search(r"\[[^\]]+\]", details) and camp_id is None:
            continue
        result.append({
            "date": item.get("date"),
            "event": item.get("event", "EVENT"),
            "details": details,
            "camp_id": camp_id,
        })
    return result


def handle_message(state: FarmState, topic: str, payload: Any) -> None:
    with state.lock:
        state.note_message(topic)

        if topic == "camp/notifications":
            if isinstance(payload, dict):
                message = str(payload.get("message") or payload.get("value") or payload)
            else:
                message = str(payload)
            state.add_notification({
                "message": message,
                "camp_id": _camp_from_text(state, message),
                "received_at": utc_now(),
            })
            state.touch()
            return

        if topic == "camp/activity_logs":
            state.set_activity(_activity_records(state, payload))
            state.touch()
            return

        if not isinstance(payload, dict):
            payload = {"value": payload}

        if topic == "camp/manager/status" or (
            topic.startswith("camp/manager/") and payload.get("service") == "camp_manager"
        ):
            state.camp_manager.update({
                "status": payload.get("status", "unknown"),
                "last_heartbeat": payload.get("observed_at") or utc_now(),
                "camps": payload.get("camps", []),
            })
            state.touch()
            return

        camp_id = camp_from_topic(topic)
        if not camp_id:
            state.touch()
            return

        camp = state.camps[camp_id]
        camp["last_seen"] = utc_now()
        data = normalize_dict(payload)

        if "/heartbeat/" in topic:
            service = topic.rsplit("/", 1)[-1]
            heartbeats = camp["system"].get("heartbeats", {})
            if service in heartbeats:
                heartbeats[service].update({
                    "status": str(data.get("status", "online")).upper(),
                    "observed_at": data.get("ts"),
                    "received_at": utc_now(),
                })

        elif "/system/status" in topic:
            camp["system"].update({
                "mqtt_connected": data.get("mqtt_connected"),
                "overall_health": data.get("overall_health", "UNKNOWN"),
                "sensors": data.get("sensors", camp["system"]["sensors"]),
                "actuators": data.get("actuators", camp["system"]["actuators"]),
                "automation": data.get("automation", camp["system"]["automation"]),
                "updated_at": data.get("updated_at"),
                "received_at": utc_now(),
            })

        elif "/irrigator/status" in topic:
            irrigator = camp["system"]["actuators"]["irrigator"]
            irrigator.update({
                "status": "ONLINE",
                "last_seen_seconds_ago": 0,
                "operation": data.get("operation", irrigator.get("operation", "unknown")),
                "active_request_id": data.get("active_request_id"),
                "last_request_id": data.get("last_request_id"),
                "last_action": data.get("last_action"),
                "last_amount": data.get("last_amount"),
                "last_completed_at": data.get("last_completed_at"),
                "observed_at": data.get("observed_at"),
                "received_at": utc_now(),
            })

        elif "/environment/telemetry" in topic:
            for key in camp["environment"]:
                if key in data and data[key] is not None:
                    camp["environment"][key] = data[key]

        elif "/terrain/telemetry" in topic:
            for key in camp["terrain"]:
                if key not in data or data[key] is None:
                    continue
                if key == "soil_moisture":
                    camp["terrain"][key] = moisture_fraction(data[key])
                elif key == "irrigation_active":
                    normalized = bool_value(data[key])
                    camp["terrain"][key] = normalized if normalized is not None else data[key]
                else:
                    camp["terrain"][key] = data[key]

        elif "/plantation/status" in topic:
            camp["plantation"].update(plantation_from_payload(data))

        state.touch()
