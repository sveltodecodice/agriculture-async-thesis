"""Versioned MQTT contract used by the web gateway.

The gateway speaks this canonical contract to future services while adapting the
existing Smart Farm topics during migration.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import uuid

SCHEMA_VERSION = "1.0"
ROOT = "farm/v1"
CAMPS = ("campo_1", "campo_2", "campo_3")

STATE_DOMAINS = ("environment", "terrain", "plantation", "manager")
ACTIONS = (
    "irrigate",
    "reoxygenate",
    "plant",
    "clear",
    "restart",
    "skip",
    "set_soil_type",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_topic(camp_id: str, domain: str) -> str:
    return f"{ROOT}/camps/{camp_id}/state/{domain}"


def event_topic(camp_id: str, event_type: str) -> str:
    return f"{ROOT}/camps/{camp_id}/events/{event_type}"


def command_topic(camp_id: str, action: str) -> str:
    return f"{ROOT}/camps/{camp_id}/commands/{action}"


def ack_topic(camp_id: str, request_id: str) -> str:
    return f"{ROOT}/camps/{camp_id}/acks/{request_id}"


def command_envelope(camp_id: str, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "camp_id": camp_id,
        "action": action,
        "params": params or {},
        "requested_at": utc_now(),
        "reply_to": ack_topic(camp_id, request_id),
        "source": "web-dashboard",
    }


def ack_envelope(
    command: dict[str, Any],
    status: str,
    *,
    detail: str = "",
    source: str = "mqtt-gateway",
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": command["request_id"],
        "camp_id": command["camp_id"],
        "action": command["action"],
        "status": status,
        "detail": detail,
        "acknowledged_at": utc_now(),
        "source": source,
    }


@dataclass(frozen=True)
class LegacyCommand:
    topic: str
    payload: str


def to_legacy_command(camp_id: str, action: str, params: dict[str, Any]) -> LegacyCommand:
    """Translate a canonical v1 action into the existing camp-manager contract."""
    if action == "irrigate":
        return LegacyCommand(f"camp/{camp_id}/camp_manager/cmd/irrigate", "trigger")
    if action == "reoxygenate":
        return LegacyCommand(f"camp/{camp_id}/camp_manager/cmd/reoxygenate", "trigger")
    if action == "plant":
        crop_key = str(params.get("crop_key", "")).strip()
        if not crop_key:
            raise ValueError("plant requires params.crop_key")
        return LegacyCommand(f"camp/{camp_id}/camp_manager/cmd/plant", crop_key)
    if action == "clear":
        return LegacyCommand(f"camp/{camp_id}/camp_manager/cmd/clear", "trigger")
    if action == "restart":
        return LegacyCommand(f"camp/{camp_id}/camp_manager/cmd/restart", "trigger")
    if action == "skip":
        days = int(params.get("days", 1))
        if not 1 <= days <= 30:
            raise ValueError("skip days must be between 1 and 30")
        return LegacyCommand(f"camp/{camp_id}/environment/cmd/skip", str(days))
    if action == "set_soil_type":
        soil_type = str(params.get("soil_type", "")).strip()
        if not soil_type:
            raise ValueError("set_soil_type requires params.soil_type")
        return LegacyCommand(f"camp/{camp_id}/terrain/cmd/set_soil_type", soil_type)
    raise ValueError(f"unsupported action: {action}")
