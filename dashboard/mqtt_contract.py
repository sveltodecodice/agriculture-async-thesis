"""Dashboard command contract.

The UI calls a simple HTTP command endpoint. This module contains the only
place that knows which legacy MQTT topic/payload each action requires.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SUPPORTED_ACTIONS = ("irrigate", "reoxygenate", "plant", "clear", "restart", "skip")


@dataclass(frozen=True)
class MqttCommand:
    topic: str
    payload: str


def build_command(camp_id: str, action: str, params: dict[str, Any]) -> MqttCommand:
    if action == "irrigate":
        return MqttCommand(f"camp/{camp_id}/camp_manager/cmd/irrigate", "trigger")
    if action == "reoxygenate":
        return MqttCommand(f"camp/{camp_id}/camp_manager/cmd/reoxygenate", "trigger")
    if action == "plant":
        seed = str(params.get("crop_key", "")).strip()
        if not seed:
            raise ValueError("plant requires crop_key")
        return MqttCommand(f"camp/{camp_id}/camp_manager/cmd/plant", seed)
    if action == "clear":
        return MqttCommand(f"camp/{camp_id}/camp_manager/cmd/clear", "trigger")
    if action == "restart":
        return MqttCommand(f"camp/{camp_id}/camp_manager/cmd/restart", "trigger")
    if action == "skip":
        days = int(params.get("days", 1))
        if not 1 <= days <= 30:
            raise ValueError("days must be between 1 and 30")
        # The environment service owns the simulated clock.
        return MqttCommand(f"camp/{camp_id}/environment/cmd/skip", str(days))
    raise ValueError(f"unsupported action: {action}")
