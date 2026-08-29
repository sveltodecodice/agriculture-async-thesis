from core.soil_moisture import get_soil_moisture
from core.oxygenation import calculate_oxygenation


def create_terrain_state(initial_moisture=50.0) -> dict:
    return {
        "soil_moisture": initial_moisture,
        "oxygenation": 100.0,
        "irrigation_active": False
    }


def process_terrain_update(state: dict, ambient_data: dict) -> dict:
    state["soil_moisture"] = get_soil_moisture(
        state["soil_moisture"],
        ambient_data["weather"],
        ambient_data["temperature"],
        state["irrigation_active"]
    )
    state["oxygenation"] = calculate_oxygenation(
        ambient_data["temperature"],
        state["soil_moisture"]
    )

    date_str = f"{ambient_data['day']:02d}/{ambient_data['month']:02d}/{ambient_data['year']}"

    return {
        "date": date_str,
        "soil_moisture": state["soil_moisture"],
        "oxygenation": state["oxygenation"],
        "irrigation_active": state["irrigation_active"]
    }