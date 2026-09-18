"""MQTT payload normalization helpers.

Sensor services are allowed to use slightly different field names. This module
converts those variations into the small schema consumed by the dashboard.
"""
from __future__ import annotations

from typing import Any

from config import CAMP_IDS
from seeds import CROP_KEY_TO_NAME, CROPS_INFO
from state_store import utc_now

EMPTY_NAMES = {"", "none", "unknown", "vacant", "empty", "field is empty", "nessuna", "clear"}

ALIASES = {
    "temp": "temperature",
    "temp_aria": "temperature",
    "humidity": "humidity_air",
    "air_humidity": "humidity_air",
    "rain": "rain_mm",
    "pioggia": "rain_mm",
    "wind": "wind_kmh",
    "vento": "wind_kmh",
    "radiation": "radiation_wm2",
    "radiazione": "radiation_wm2",
    "moisture": "soil_moisture",
    "umidita_suolo": "soil_moisture",
    "oxygen": "oxygenation",
    "ossigenazione": "oxygenation",
    "water_applied_mm": "water_dispensed_mm",
    "erogata": "water_dispensed_mm",
    "terrain_type": "soil_type",
}


def normalize_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {ALIASES.get(str(key).lower(), key): value for key, value in payload.items()}


def camp_from_topic(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) >= 2 and parts[0] == "camp" and parts[1] in CAMP_IDS:
        return parts[1]
    return None


def moisture_fraction(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number / 100.0 if abs(number) > 1.0 else number


def bool_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return None


def display_crop(raw: Any) -> tuple[str, str | None]:
    text = str(raw or "").strip()
    key = text.lower().replace("-", "_")
    if key in EMPTY_NAMES:
        return "Nessuna", None
    mapped = CROP_KEY_TO_NAME.get(key) or CROP_KEY_TO_NAME.get(key.replace("_", " "))
    return mapped or text, key or None


def plantation_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse the current nested plantation/status payload from the manager/sensor."""
    data = normalize_dict(payload)
    detail = data.get("status_detail") if isinstance(data.get("status_detail"), dict) else {}
    raw_name = detail.get("plant_name") or data.get("crop") or data.get("plant") or data.get("seed_name") or data.get("name")
    crop, crop_key = display_crop(raw_name)
    available = bool_value(data.get("camp_availability"))
    occupied = (available is True and crop != "Nessuna") if "camp_availability" in data else crop != "Nessuna"

    if not occupied:
        return {
            "crop": "Nessuna", "crop_key": None, "occupied": False,
            "time_left": None, "growth_percentage": 0.0, "growth_stage": "EMPTY",
            "health": "FIELD IS EMPTY", "min_moisture": None, "max_moisture": None,
            "min_temperature": None, "max_temperature": None, "ideal_soil": None,
            "harvest_days": None, "seasons": [], "last_status_at": utc_now(),
        }

    meta = CROPS_INFO.get(crop, {})
    min_m = moisture_fraction(detail.get("min_soilmoisture"))
    max_m = moisture_fraction(detail.get("max_soilmoisture"))
    return {
        "crop": crop,
        "crop_key": crop_key,
        "occupied": True,
        "time_left": detail.get("time_left", data.get("time_left")),
        "growth_percentage": detail.get("growth_percentage", data.get("growth_percentage", 0.0)),
        "growth_stage": detail.get("growth_stage", data.get("growth_stage", "UNKNOWN")),
        "health": detail.get("health", data.get("health", "UNKNOWN")),
        "min_moisture": min_m if min_m is not None else meta.get("threshold"),
        "max_moisture": max_m if max_m is not None else meta.get("max_threshold"),
        "min_temperature": meta.get("min_temp"),
        "max_temperature": meta.get("max_temp"),
        "ideal_soil": meta.get("ideal_soil"),
        "harvest_days": meta.get("days"),
        "seasons": meta.get("seasons", []),
        "last_status_at": utc_now(),
    }
