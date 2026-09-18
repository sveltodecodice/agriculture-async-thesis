"""Read-only projections of Camp Manager decision rules for the dashboard.

These helpers explain what the Camp Manager is expected to do from currently
observed telemetry. They never execute farm actions and never replace manager
state. The formulas intentionally mirror the current Camp Manager codebase.
"""
from __future__ import annotations

from typing import Any

from seeds import SEEDS_LST
from config_loader import env_value

AUTO_SEED_EMPTY_DAYS = env_value("AUTO_SEED_EMPTY_DAYS", "automation.planting.empty_days_before_auto_seed", 3, int)
OXYGENATION_THRESHOLD_PCT = env_value("OXYGENATION_THRESHOLD", "automation.oxygenation.minimum_percentage", 30.0, float)
EMPTY_FIELD_MIN_MOISTURE_PCT = env_value("EMPTY_FIELD_MIN_MOISTURE", "automation.irrigation.empty_field_min_moisture", 15.0, float)
IRRIGATION_TARGET_MARGIN_PCT = env_value("IRRIGATION_TARGET_MARGIN", "automation.irrigation.target_margin", 5.0, float)
MIN_IRRIGATION_AMOUNT_PCT = env_value("MIN_IRRIGATION_AMOUNT", "automation.irrigation.minimum_amount_pct", 2.0, float)


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percent_from_fraction(value: Any) -> float | None:
    number = _number(value)
    if number is None:
        return None
    return number * 100.0 if abs(number) <= 1.0 else number


def _season_ok(seed: dict[str, Any], season: str | None) -> bool:
    if not season:
        return False
    return str(season).lower() in [
        str(item).lower() for item in seed.get("seasons", [])
    ]


def _normalize_soil(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def _soil_ok(seed: dict[str, Any], soil_type: str | None) -> bool:
    if not soil_type:
        return False
    return _normalize_soil(seed.get("ideal_soil")) == _normalize_soil(soil_type)


def top_seed_candidates(
    moisture_pct: float | None,
    season: str | None,
    soil_type: str | None = None,
) -> list[dict[str, Any]]:
    """Mirror Camp Manager ranking: season -> soil -> moisture."""
    if moisture_pct is None:
        moisture_pct = 28.0

    ranked = sorted(
        SEEDS_LST,
        key=lambda seed: (
            0 if _season_ok(seed, season) else 1,
            0 if _soil_ok(seed, soil_type) else 1,
            abs(float(seed.get("min_soilmoisture", 20.0)) - moisture_pct),
            str(seed.get("name", "")),
        ),
    )[:3]

    return [
        {
            "key": seed["name"],
            "name": seed.get("name_it", seed["name"]),
            "min_moisture_pct": float(seed.get("min_soilmoisture", 0.0)),
            "max_moisture_pct": float(seed.get("max_soilmoisture", 0.0)),
            "ideal_soil": seed.get("ideal_soil"),
            "seasons": seed.get("seasons", []),
            "season_match": _season_ok(seed, season),
            "soil_match": _soil_ok(seed, soil_type),
            "distance_from_current_pct": round(
                abs(float(seed.get("min_soilmoisture", 20.0)) - moisture_pct), 1
            ),
        }
        for seed in ranked
    ]


def manager_policy(camp: dict[str, Any]) -> dict[str, Any]:
    """Build a read-only explanation of current Camp Manager automation policy."""
    env = camp.get("environment") or {}
    terrain = camp.get("terrain") or {}
    plantation = camp.get("plantation") or {}
    system = camp.get("system") or {}
    automation = system.get("automation") or {}
    irrigation_pending = bool((automation.get("irrigation") or {}).get("pending"))
    reoxygenation_pending = bool((automation.get("reoxygenation") or {}).get("pending"))

    occupied = bool(plantation.get("occupied"))
    moisture_pct = _percent_from_fraction(terrain.get("soil_moisture"))
    plant_min_pct = _percent_from_fraction(plantation.get("min_moisture"))
    target_min_pct = plant_min_pct if occupied and plant_min_pct is not None else EMPTY_FIELD_MIN_MOISTURE_PCT
    target_after_pct = target_min_pct + IRRIGATION_TARGET_MARGIN_PCT

    auto_irrigation_required = (
        moisture_pct is not None
        and moisture_pct < target_min_pct
        and not irrigation_pending
    )
    needed_water_pct = None
    if moisture_pct is not None:
        needed_water_pct = round(
            max(MIN_IRRIGATION_AMOUNT_PCT, target_after_pct - moisture_pct), 1
        )

    oxygenation_pct = _number(terrain.get("oxygenation"))
    auto_reoxygenation_required = (
        oxygenation_pct is not None
        and oxygenation_pct < OXYGENATION_THRESHOLD_PCT
        and not reoxygenation_pending
    )

    time_left = _number(plantation.get("time_left"))
    auto_harvest_required = bool(occupied and time_left is not None and time_left <= 0)

    candidates = top_seed_candidates(
        moisture_pct,
        env.get("season"),
        terrain.get("soil_type"),
    )

    return {
        "irrigation": {
            "current_moisture_pct": round(moisture_pct, 1) if moisture_pct is not None else None,
            "target_min_pct": round(target_min_pct, 1),
            "target_after_pct": round(target_after_pct, 1),
            "needed_water_pct": needed_water_pct,
            "automatic_required": auto_irrigation_required,
            "pending": irrigation_pending,
        },
        "oxygenation": {
            "current_pct": round(oxygenation_pct, 1) if oxygenation_pct is not None else None,
            "threshold_pct": OXYGENATION_THRESHOLD_PCT,
            "automatic_required": auto_reoxygenation_required,
            "pending": reoxygenation_pending,
        },
        "harvest": {
            "automatic_required": auto_harvest_required,
            "time_left": time_left,
        },
        "seeding": {
            "automatic_after_empty_days": AUTO_SEED_EMPTY_DAYS,
            "season": env.get("season"),
            "soil_type": terrain.get("soil_type"),
            "current_moisture_pct": round(moisture_pct, 1) if moisture_pct is not None else None,
            "candidates": candidates,
            "counter_exposed": False,
        },
    }
