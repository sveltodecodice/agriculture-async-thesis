from core.soil_moisture import get_soil_moisture
from core.oxygenation import calculate_oxygenation


def create_terrain_state(initial_moisture=50.0) -> dict:
    return {
        "soil_moisture": initial_moisture,
        "oxygenation": 100.0,
        "irrigation_active": False
    }


def update_terrain(state: dict, weather: str, temperature: float):
    # 1. Pass irrigation_active directly to get_soil_moisture
    state["soil_moisture"] = get_soil_moisture(
        state["soil_moisture"],
        weather,
        temperature,
        state["irrigation_active"]
    )

    # 2. Correct parameter order: (temperature, soil_moisture)
    state["oxygenation"] = calculate_oxygenation(
        temperature,
        state["soil_moisture"]
    )

    return state