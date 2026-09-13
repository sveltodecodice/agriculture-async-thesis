from typing import Any, Dict, Optional
from common.constants import SEEDS_LST


def create_default_plantation_state() -> Dict[str, Any]:
    """Creates a default, unoccupied plantation state dictionary.

    Returns:
        Dict[str, Any]: A dictionary initialized with default state values.
    """
    return {
        "occupied": False,
        "plant_name": None,
        "min_moisture": 0.0,
        "max_moisture": 0.0,
        "min_temp": 0.0,
        "max_temp": 0.0,
        "seasons": [],
        "time_left": 0,
        "total_days": 0,
    }


def seed_planted(plantation_state: Dict[str, Any], seed: Any) -> None:
    """Updates the plantation state with configuration for a newly planted seed.

    Args:
        plantation_state (Dict[str, Any]): The current state dictionary of the plantation.
        seed (Any): Seed information provided as a dictionary or a string identifier.
    """
    if isinstance(seed, dict):
        plant_name = (
            seed.get("name")
            or seed.get("seed")
            or seed.get("plant_name")
            or "Unknown"
        )
    else:
        plant_name = str(seed).strip()

    search_term = plant_name.lower()
    full_seed = next(
        (s for s in SEEDS_LST if s["name"].lower() == search_term), None
    )

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
    min_temp = (
        full_seed.get("min_temperature")
        if full_seed
        else (seed.get("min_temperature") if isinstance(seed, dict) else 10.0)
    )
    max_temp = (
        full_seed.get("max_temperature")
        if full_seed
        else (seed.get("max_temperature") if isinstance(seed, dict) else 30.0)
    )
    seasons = (
        full_seed.get("seasons")
        if full_seed
        else (seed.get("seasons") if isinstance(seed, dict) else [])
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
    plantation_state["min_temp"] = float(
        min_temp if min_temp is not None else 10.0
    )
    plantation_state["max_temp"] = float(
        max_temp if max_temp is not None else 30.0
    )
    plantation_state["seasons"] = list(seasons) if seasons else []

    if isinstance(harvest_time, (list, tuple)):
        initial_days = int(harvest_time[0])
    else:
        initial_days = int(harvest_time) if harvest_time is not None else 5

    plantation_state["time_left"] = initial_days
    plantation_state["total_days"] = initial_days


def clear_field(plantation_state: Dict[str, Any]) -> None:
    """Clears the plantation field and resets state attributes to default.

    Args:
        plantation_state (Dict[str, Any]): The current state dictionary of the plantation.
    """
    plantation_state["occupied"] = False
    plantation_state["plant_name"] = None
    plantation_state["min_moisture"] = 0.0
    plantation_state["max_moisture"] = 0.0
    plantation_state["min_temp"] = 0.0
    plantation_state["max_temp"] = 0.0
    plantation_state["seasons"] = []
    plantation_state["time_left"] = 0
    plantation_state["total_days"] = 0


def reset(plantation_state: Dict[str, Any]) -> None:
    """Resets the plantation state back to an empty field.

    Args:
        plantation_state (Dict[str, Any]): The current state dictionary of the plantation.
    """
    clear_field(plantation_state)


def advance_days(
    plantation_state: Dict[str, Any], days_passed: int = 1
) -> None:
    """Advances time for the plantation, reducing the time left until harvest.

    Args:
        plantation_state (Dict[str, Any]): The current state dictionary of the plantation.
        days_passed (int, optional): Number of days to advance. Defaults to 1.
    """
    if plantation_state["occupied"] and plantation_state["time_left"] > 0:
        plantation_state["time_left"] = max(
            0, plantation_state["time_left"] - days_passed
        )


def get_growth_percentage(plantation_state: Dict[str, Any]) -> float:
    """Calculates the current growth percentage of the crop.

    Args:
        plantation_state (Dict[str, Any]): The current state dictionary of the plantation.

    Returns:
        float: Crop growth progress percentage rounded to 1 decimal place.
    """
    if not plantation_state["occupied"] or plantation_state.get("total_days", 0) <= 0:
        return 0.0

    elapsed_days = plantation_state["total_days"] - plantation_state["time_left"]
    percentage = (elapsed_days / plantation_state["total_days"]) * 100.0
    return round(min(100.0, max(0.0, percentage)), 1)


def get_growth_stage(plantation_state: Dict[str, Any]) -> str:
    """Determines the semantic growth stage based on current growth percentage.

    Args:
        plantation_state (Dict[str, Any]): The current state dictionary of the plantation.

    Returns:
        str: Growth stage string ('EMPTY', 'PLANTED', 'GERMINATION',
        'VEGETATIVE', 'MATURING', or 'READY_FOR_HARVEST').
    """
    if not plantation_state["occupied"]:
        return "EMPTY"

    progress = get_growth_percentage(plantation_state)
    if progress == 0.0:
        return "PLANTED"
    if progress < 25.0:
        return "GERMINATION"
    if progress < 75.0:
        return "VEGETATIVE"
    if progress < 100.0:
        return "MATURING"
    return "READY_FOR_HARVEST"


def check_health(
    plantation_state: Dict[str, Any],
    current_moisture: Optional[float] = None,
    current_temp: Optional[float] = None,
    current_season: Optional[str] = None,
) -> str:
    """Evaluates crop health across soil moisture, ambient temperature, and season.

    Args:
        plantation_state (Dict[str, Any]): The current state dictionary of the plantation.
        current_moisture (Optional[float], optional): Current soil moisture reading.
        current_temp (Optional[float], optional): Current ambient temperature reading.
        current_season (Optional[str], optional): Current season identifier.

    Returns:
        str: Comma-separated issue descriptions or 'HEALTHY' if conditions are optimal.
    """
    if not plantation_state["occupied"]:
        return "FIELD IS EMPTY"

    issues = []

    if current_moisture is not None:
        if current_moisture < plantation_state["min_moisture"]:
            issues.append("TOO_DRY")
        elif current_moisture > plantation_state["max_moisture"]:
            issues.append("TOO_WET")

    if current_temp is not None:
        if current_temp < plantation_state.get("min_temp", 0.0):
            issues.append("TOO_COLD")
        elif current_temp > plantation_state.get("max_temp", 50.0):
            issues.append("TOO_HOT")

    if current_season and plantation_state.get("seasons"):
        valid_seasons = [s.lower() for s in plantation_state["seasons"]]
        if current_season.lower() not in valid_seasons:
            issues.append("UNFAVORABLE_SEASON")

    return ", ".join(issues) if issues else "HEALTHY"


def get_status(
    plantation_state: Dict[str, Any],
    current_moisture: Optional[float] = None,
    current_temp: Optional[float] = None,
    current_season: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves a summarized status report of plantation state, growth, and health.

    Args:
        plantation_state (Dict[str, Any]): The current state dictionary of the plantation.
        current_moisture (Optional[float], optional): Current soil moisture reading.
        current_temp (Optional[float], optional): Current ambient temperature reading.
        current_season (Optional[str], optional): Current season identifier.

    Returns:
        Dict[str, Any]: Nested dictionary containing field availability and detailed crop status.
    """
    ready_to_harvest = (
        plantation_state["occupied"] and plantation_state["time_left"] == 0
    )

    if not plantation_state["occupied"]:
        plant_status = {
            "plant_name": "None",
            "time_left": 0,
            "growth_percentage": 0.0,
            "growth_stage": "EMPTY",
            "ready_to_harvest": False,
            "health": "FIELD IS EMPTY",
            "min_soilmoisture": 0.0,
            "max_soilmoisture": 0.0,
            "min_temperature": 0.0,
            "max_temperature": 0.0,
        }
    else:
        plant_status = {
            "plant_name": plantation_state["plant_name"],
            "time_left": plantation_state["time_left"],
            "growth_percentage": get_growth_percentage(plantation_state),
            "growth_stage": get_growth_stage(plantation_state),
            "ready_to_harvest": ready_to_harvest,
            "health": check_health(
                plantation_state, current_moisture, current_temp, current_season
            ),
            "min_soilmoisture": plantation_state["min_moisture"],
            "max_soilmoisture": plantation_state["max_moisture"],
            "min_temperature": plantation_state["min_temp"],
            "max_temperature": plantation_state["max_temp"],
        }

    return {
        "camp_availability": plantation_state["occupied"],
        "status_detail": plant_status,
    }