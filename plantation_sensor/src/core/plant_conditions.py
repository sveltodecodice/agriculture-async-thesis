from common.constants import SEEDS_LST


def create_default_plantation_state() -> dict:
    """Creates a default, unoccupied plantation state dictionary.

    Returns:
        dict: A dictionary initialized with default state values.
    """
    return {
        "occupied": False,
        "plant_name": None,
        "min_moisture": 0.0,
        "max_moisture": 0.0,
        "time_left": 0,
    }


def seed_planted(plantation_state: dict, seed: dict) -> None:
    """Updates the plantation state with configuration for a newly planted seed.

    Args:
        plantation_state (dict): The current state dictionary of the plantation.
        seed (dict): Seed information provided as a dictionary or a string identifier.
    """
    if isinstance(seed, dict):
        plant_name = (
            seed.get("name") or seed.get("seed") or seed.get("plant_name") or "Unknown"
        )
    else:
        plant_name = str(seed).strip()

    search_term = plant_name.lower()
    full_seed = next((s for s in SEEDS_LST if s["name"].lower() == search_term), None)

    plantation_state["occupied"] = True
    plantation_state["plant_name"] = (
        full_seed["name"].capitalize() if full_seed else plant_name.capitalize()
    )

    min_moisture = (
        full_seed.get("min_soilmoisture")
        if full_seed
        else (seed.get("min_soilmoisture") if isinstance(seed, dict) else 20.0)
    )
    max_moisture = (
        full_seed.get("max_soilmoisture")
        if full_seed
        else (seed.get("max_soilmoisture") if isinstance(seed, dict) else 80.0)
    )
    harvest_time = (
        full_seed.get("time_harvest")
        if full_seed
        else (seed.get("time_harvest") if isinstance(seed, dict) else 5)
    )

    plantation_state["min_moisture"] = float(
        min_moisture if min_moisture is not None else 20.0
    )
    plantation_state["max_moisture"] = float(
        max_moisture if max_moisture is not None else 80.0
    )

    if isinstance(harvest_time, (list, tuple)):
        plantation_state["time_left"] = int(harvest_time[0])
    else:
        plantation_state["time_left"] = (
            int(harvest_time) if harvest_time is not None else 5
        )


def clear_field(plantation_state: dict) -> None:
    """Clears the plantation field and resets state attributes to default.

    Args:
        plantation_state (dict): The current state dictionary of the plantation.
    """
    plantation_state["occupied"] = False
    plantation_state["plant_name"] = None
    plantation_state["min_moisture"] = 0.0
    plantation_state["max_moisture"] = 0.0
    plantation_state["time_left"] = 0


def reset(plantation_state: dict) -> None:
    """Resets the plantation state back to an empty field.

    Args:
        plantation_state (dict): The current state dictionary of the plantation.
    """
    clear_field(plantation_state)


def advance_days(plantation_state: dict, days_passed: int = 1) -> None:
    """Advances time for the plantation, reducing the time left until harvest.

    Args:
        plantation_state (dict): The current state dictionary of the plantation.
        days_passed (int, optional): Number of days to advance. Defaults to 1.
    """
    if plantation_state["occupied"] and plantation_state["time_left"] > 0:
        plantation_state["time_left"] = max(
            0, plantation_state["time_left"] - days_passed
        )


def check_health(plantation_state: dict, current_moisture=None) -> str:
    """Evaluates crop health based on current soil moisture levels.

    Args:
        plantation_state (dict): The current state dictionary of the plantation.
        current_moisture (None | float): Current soil moisture reading.

    Returns:
        str: Status string indicating field state ('FIELD IS EMPTY', 'HEALTHY',
        'TOO_DRY', or 'TOO_WET').
    """
    if not plantation_state["occupied"]:
        return "FIELD IS EMPTY"
    if current_moisture is None:
        return "HEALTHY"
    if current_moisture < plantation_state["min_moisture"]:
        return "TOO_DRY"
    if current_moisture > plantation_state["max_moisture"]:
        return "TOO_WET"
    return "HEALTHY"


def get_status(plantation_state: dict, current_moisture=None) -> dict:
    """Retrieves a summarized status report of the plantation state and crop health.

    Args:
        plantation_state (dict): The current state dictionary of the plantation.
        current_moisture (None | float): Current soil moisture level. Defaults to None.

    Returns:
        dict: Nested dictionary containing field availability and detailed crop status.
    """
    ready_to_harvest = (
        plantation_state["occupied"] and plantation_state["time_left"] == 0
    )

    if not plantation_state["occupied"]:
        plant_status = {
            "plant_name": "None",
            "time_left": 0,
            "ready_to_harvest": False,
            "health": "FIELD IS EMPTY",
            "min_soilmoisture": 0.0,
            "max_soilmoisture": 0.0,
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
        "status_detail": plant_status,
    }
