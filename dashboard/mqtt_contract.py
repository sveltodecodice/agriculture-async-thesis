"""MQTT contract for operator commands issued by the dashboard.

Normal operational actions are sent to Camp Manager. Camp Manager remains the
orchestrator and forwards the action to Seeder, Harvester, or Irrigator when
appropriate. The only deliberate exception is ``skip``: the Ambient Sensor owns
the simulated clock, so that administrative simulation command is sent directly
to the environment service.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

SUPPORTED_ACTIONS = ("irrigate", "reoxygenate", "plant", "clear", "restart", "skip")


@dataclass(frozen=True)
class MqttCommand:
    topic: str
    payload: str
    target_service: str


def build_command(camp_id: str, action: str, params: dict[str, Any]) -> MqttCommand:
    if action == "irrigate":
        return MqttCommand(
            f"camp/{camp_id}/camp_manager/cmd/irrigate",
            "trigger",
            "Camp Manager -> Irrigator",
        )

    if action == "reoxygenate":
        return MqttCommand(
            f"camp/{camp_id}/camp_manager/cmd/reoxygenate",
            "trigger",
            "Camp Manager -> Irrigator",
        )

    if action == "plant":
        seed = str(params.get("crop_key", "")).strip()
        if not seed:
            raise ValueError("plant requires crop_key")
        return MqttCommand(
            f"camp/{camp_id}/camp_manager/cmd/plant",
            json.dumps({"seed": seed}),
            "Camp Manager -> Seeder",
        )

    if action == "clear":
        return MqttCommand(
            f"camp/{camp_id}/camp_manager/cmd/clear",
            "trigger",
            "Camp Manager",
        )

    if action == "restart":
        return MqttCommand(
            f"camp/{camp_id}/camp_manager/cmd/restart",
            "trigger",
            "Camp Manager",
        )

    if action == "skip":
        days = int(params.get("days", 1))
        if not 1 <= days <= 30:
            raise ValueError("days must be between 1 and 30")
        return MqttCommand(
            f"camp/{camp_id}/environment/cmd/skip",
            str(days),
            "Ambient Sensor",
        )

    raise ValueError(f"unsupported action: {action}")
