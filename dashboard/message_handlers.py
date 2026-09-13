"""Functions that apply MQTT messages to FarmState."""
from __future__ import annotations

from typing import Any

from normalizers import bool_value, camp_from_topic, moisture_fraction, normalize_dict, plantation_from_payload
from state_store import FarmState, utc_now


def handle_message(state: FarmState, topic: str, payload: Any) -> None:
    if not isinstance(payload, dict):
        payload = {"value": payload}

    with state.lock:
        state.note_message(topic)

        if topic == "camp/manager/status" or (topic.startswith("camp/manager/") and payload.get("service") == "camp_manager"):
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

        if "/system/status" in topic:
            camp["system"].update({
                "mqtt_connected": data.get("mqtt_connected"),
                "overall_health": data.get("overall_health", "UNKNOWN"),
                "sensors": data.get("sensors", camp["system"]["sensors"]),
                "updated_at": data.get("updated_at"),
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
