"""Terrain state initialization and natural update processing."""

from typing import Any, Dict

from common.parameters import FIELD_NAME
from core.oxygenation import calculate_oxygenation
from core.soil_moisture import get_soil_moisture


def create_terrain_state(
    initial_moisture: float = 30.0,
    initial_oxygen: float = 70.0,
    soil_type: str = "Franco",
) -> Dict[str, Any]:
    """Initialize observed terrain state.

    Actuator state is not owned by the Terrain Sensor. The compatibility
    field ``irrigation_active`` starts False and remains observational.
    """
    return {
        "camp_id": FIELD_NAME,
        "soil_moisture": initial_moisture,
        "oxygenation": initial_oxygen,
        "soil_type": soil_type,
        "irrigation_active": False,
        "water_dispensed_mm": 0.0,
        "last_irrigation_amount_pct": 0.0,
        "last_irrigation_id": None,
        "last_reoxygenation_id": None,
        "last_action": None,
        "date": "01/01/2026",
    }


def terrain_telemetry(state: Dict[str, Any]) -> Dict[str, Any]:
    """Build the public Terrain Sensor telemetry payload."""
    return {
        "date": state.get("date", "01/01/2026"),
        "soil_moisture": state["soil_moisture"],
        "oxygenation": state["oxygenation"],
        "soil_type": state.get("soil_type", "Franco"),
        # Kept for backward compatibility. Actuator execution state is now
        # published by the Irrigator and aggregated by Camp Manager.
        "irrigation_active": False,
        "water_dispensed_mm": state.get("water_dispensed_mm", 0.0),
        "last_irrigation_amount_pct": state.get("last_irrigation_amount_pct", 0.0),
        "last_irrigation_id": state.get("last_irrigation_id"),
        "last_reoxygenation_id": state.get("last_reoxygenation_id"),
        "last_action": state.get("last_action"),
    }


def process_terrain_update(
    state: Dict[str, Any], ambient_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply only natural environment effects to terrain state."""
    state["soil_moisture"] = get_soil_moisture(
        current_moisture=state["soil_moisture"],
        temperature=ambient_data.get("temperature", 20.0),
        rain_mm=ambient_data.get("rain_mm", 0.0),
        radiation_wm2=ambient_data.get("radiation_wm2", 500.0),
        wind_kmh=ambient_data.get("wind_kmh", 10.0),
        soil_type=state.get("soil_type", "Franco"),
    )

    state["oxygenation"] = calculate_oxygenation(
        state["oxygenation"],
        ambient_data.get("temperature", 20.0),
        state["soil_moisture"],
    )

    date_str = ambient_data.get("date")
    if not date_str and "day" in ambient_data:
        date_str = (
            f"{ambient_data['day']:02d}/"
            f"{ambient_data['month']:02d}/"
            f"{ambient_data['year']}"
        )
    elif not date_str:
        date_str = state.get("date", "01/01/2026")

    state["date"] = date_str

    # water_dispensed_mm describes the current update. Natural evolution
    # does not dispense actuator water.
    state["water_dispensed_mm"] = 0.0

    return terrain_telemetry(state)
