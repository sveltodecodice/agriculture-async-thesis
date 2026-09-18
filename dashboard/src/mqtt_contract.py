"""MQTT topics used by dashboard operator commands."""
import json
from typing import Any

SUPPORTED_ACTIONS = ("irrigate", "reoxygenate", "plant", "clear", "restart", "skip")


def build_command(camp_id: str, action: str, params: dict[str, Any]) -> dict[str, str]:
    manager = f"camp/{camp_id}/camp_manager/cmd"

    if action == "irrigate":
        return {"topic": f"{manager}/irrigate", "payload": "trigger", "target_service": "Camp Manager -> Irrigator"}
    if action == "reoxygenate":
        return {"topic": f"{manager}/reoxygenate", "payload": "trigger", "target_service": "Camp Manager -> Irrigator"}
    if action == "plant":
        seed = str(params.get("crop_key", "")).strip()
        if not seed:
            raise ValueError("La semina richiede la selezione di una coltura")
        return {"topic": f"{manager}/plant", "payload": json.dumps({"seed": seed}), "target_service": "Camp Manager -> Seeder"}
    if action == "clear":
        return {"topic": f"{manager}/clear", "payload": "trigger", "target_service": "Camp Manager"}
    if action == "restart":
        return {"topic": f"{manager}/restart", "payload": "trigger", "target_service": "Camp Manager"}
    if action == "skip":
        days = int(params.get("days", 1))
        if not 1 <= days <= 30:
            raise ValueError("I giorni devono essere compresi tra 1 e 30")
        return {"topic": f"camp/{camp_id}/environment/cmd/skip", "payload": str(days), "target_service": "Ambient Sensor"}

    raise ValueError(f"Operazione non supportata: {action}")
