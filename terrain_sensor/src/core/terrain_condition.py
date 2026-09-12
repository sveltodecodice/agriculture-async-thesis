from core.soil_moisture import get_soil_moisture
from core.oxygenation import calculate_oxygenation, apply_reoxygenation


def create_terrain_state(
    initial_moisture=30.0, initial_oxygen=70.0, soil_type="Franco"
) -> dict:
    return {
        "soil_moisture": initial_moisture,
        "oxygenation": initial_oxygen,
        "soil_type": soil_type,
        "irrigation_active": False,
        "water_dispensed_mm": 0.0,
    }


def process_terrain_update(state: dict, ambient_data: dict) -> dict:
    new_moisture, water_mm = get_soil_moisture(
        current_moisture=state["soil_moisture"],
        weather=ambient_data.get("weather", "Sunny"),
        temperature=ambient_data.get("temperature", 20.0),
        active_irrigation=state["irrigation_active"],
        rain_mm=ambient_data.get("rain_mm", 0.0),
        radiation_wm2=ambient_data.get("radiation_wm2", 500.0),
        wind_kmh=ambient_data.get("wind_kmh", 10.0),
        soil_type=state.get("soil_type", "Franco"),
    )

    state["soil_moisture"] = new_moisture
    state["water_dispensed_mm"] = water_mm

    o2 = calculate_oxygenation(
        state["oxygenation"],
        ambient_data.get("temperature", 20.0),
        state["soil_moisture"],
    )

    state["oxygenation"] = apply_reoxygenation(
        o2, minimal_oxygenation=20.0, reoxygenation=60.0
    )

    date_str = ambient_data.get("date")
    if not date_str and "day" in ambient_data:
        date_str = f"{ambient_data['day']:02d}/{ambient_data['month']:02d}/{ambient_data['year']}"
    elif not date_str:
        date_str = "01/01/2026"

    state["date"] = date_str

    return {
        "date": date_str,
        "soil_moisture": state["soil_moisture"],
        "oxygenation": state["oxygenation"],
        "soil_type": state.get("soil_type", "Franco"),
        "irrigation_active": state["irrigation_active"],
        "water_dispensed_mm": state["water_dispensed_mm"],
    }
