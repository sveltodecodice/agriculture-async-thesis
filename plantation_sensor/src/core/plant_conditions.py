
from common.constants import SEEDS_LST


def create_default_plantation_state():
    return {
        "occupied": False,
        "plant_name": None,
        "min_moisture": 0.0,
        "max_moisture": 0.0,
        "time_left": 0
    }


def seed_planted(plantation_state: dict, seed):
    if isinstance(seed, dict):
        p_name = seed.get("name") or seed.get("seed") or seed.get("plant_name") or "Unknown"
    else:
        p_name = str(seed).strip()

    search_term = p_name.lower()
    full_seed = next((s for s in SEEDS_LST if s["name"].lower() == search_term), None)

    plantation_state["occupied"] = True
    plantation_state["plant_name"] = full_seed["name"].capitalize() if full_seed else p_name.capitalize()

    min_m = full_seed.get("min_soilmoisture") if full_seed else (seed.get("min_soilmoisture") if isinstance(seed, dict) else 20.0)
    max_m = full_seed.get("max_soilmoisture") if full_seed else (seed.get("max_soilmoisture") if isinstance(seed, dict) else 80.0)
    harvest_t = full_seed.get("time_harvest") if full_seed else (seed.get("time_harvest") if isinstance(seed, dict) else 5)

    plantation_state["min_moisture"] = float(min_m if min_m is not None else 20.0)
    plantation_state["max_moisture"] = float(max_m if max_m is not None else 80.0)

    if isinstance(harvest_t, (list, tuple)):
        plantation_state["time_left"] = int(harvest_t[0])
    else:
        plantation_state["time_left"] = int(harvest_t) if harvest_t is not None else 5


def clear_field(plantation_state: dict):
    plantation_state["occupied"] = False
    plantation_state["plant_name"] = None
    plantation_state["min_moisture"] = 0.0
    plantation_state["max_moisture"] = 0.0
    plantation_state["time_left"] = 0


def reset(plantation_state: dict):
    clear_field(plantation_state)


def advance_days(plantation_state: dict, days_passed: int = 1):
    if plantation_state["occupied"] and plantation_state["time_left"] > 0:
        plantation_state["time_left"] = max(0, plantation_state["time_left"] - days_passed)


def check_health(plantation_state: dict, current_moisture: float) -> str:
    if not plantation_state["occupied"]:
        return "FIELD IS EMPTY"
    if current_moisture is None:
        return "HEALTHY"
    if current_moisture < plantation_state["min_moisture"]:
        return "TOO_DRY"
    if current_moisture > plantation_state["max_moisture"]:
        return "TOO_WET"
    return "HEALTHY"


def get_status(plantation_state: dict, current_moisture: float = None) -> dict:
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
            "health": check_health(plantation_state, current_moisture),
            "min_soilmoisture": plantation_state["min_moisture"],
            "max_soilmoisture": plantation_state["max_moisture"],
        }

    return {
        "camp_availability": plantation_state["occupied"],
        "status_detail": plant_status
    }