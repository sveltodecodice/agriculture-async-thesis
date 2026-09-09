plantation_state = {
    "occupied": False,
    "plant_name": None,
    "min_moisture": 0.0,
    "max_moisture": 0.0,
    "time_left": 0
}


def seed_planted(seed: dict):
    plantation_state["occupied"] = True
    plantation_state["plant_name"] = seed["name"]
    plantation_state["min_moisture"] = seed.get("min_soilmoisture", 20.0)
    plantation_state["max_moisture"] = seed.get("max_soilmoisture", 80.0)
    
    harvest_time = seed.get("time_harvest", 5)
    if isinstance(harvest_time, (list, tuple)):
        plantation_state["time_left"] = harvest_time[0]
    else:
        plantation_state["time_left"] = int(harvest_time)


def clear_field():
    plantation_state["occupied"] = False
    plantation_state["plant_name"] = None
    plantation_state["min_moisture"] = 0.0
    plantation_state["max_moisture"] = 0.0
    plantation_state["time_left"] = 0


def reset():
    clear_field()


def advance_days(days_passed: int = 1):
    if plantation_state["occupied"] and plantation_state["time_left"] > 0:
        plantation_state["time_left"] = max(0, plantation_state["time_left"] - days_passed)


def check_health(current_moisture: float) -> str:
    if not plantation_state["occupied"]:
        return "FIELD IS EMPTY"
    if current_moisture < plantation_state["min_moisture"]:
        return "TOO_DRY"
    if current_moisture > plantation_state["max_moisture"]:
        return "TOO_WET"
    return "HEALTHY"


def get_status(current_moisture: float = None) -> dict:
    ready_to_harvest = plantation_state["occupied"] and plantation_state["time_left"] == 0

    if not plantation_state["occupied"]:
        plant_status = {
            "plant_name": "None",
            "time_left": 0,
            "ready_to_harvest": False,
            "health": "FIELD IS EMPTY",
            "min_soilmoisture": 0.0,
            "max_soilmoisture": 0.0
        }
    else:
        plant_status = {
            "plant_name": plantation_state["plant_name"],
            "time_left": plantation_state["time_left"],
            "ready_to_harvest": ready_to_harvest,
            "health": check_health(current_moisture) if current_moisture is not None else "UNKNOWN",
            "min_soilmoisture": plantation_state["min_moisture"],
            "max_soilmoisture": plantation_state["max_moisture"],
        }

    return {
        "camp_availability": plantation_state["occupied"],
        "status_detail": plant_status
    }