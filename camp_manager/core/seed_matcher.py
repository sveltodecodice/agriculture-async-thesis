from core.seeds import list_seeds


def is_season_ok(seed: dict, season: str) -> bool:
    """Checks if the given season matches the seed's allowed seasons."""
    if not season:
        return False
    return season.lower() in [s.lower() for s in seed.get("seasons", [])]


def is_moisture_ok(seed: dict, moisture: float) -> bool:
    """Checks if the soil moisture is within the seed's ideal range."""
    return seed["min_soilmoisture"] <= moisture <= seed["max_soilmoisture"]


def evaluate_seed(seed: dict, moisture: float, season: str) -> dict:
    """Returns seed details if both season and moisture match, otherwise None."""
    if is_season_ok(seed, season) and is_moisture_ok(seed, moisture):
        return {
            "name": seed["name"],
            "min_soilmoisture": seed["min_soilmoisture"],
            "max_soilmoisture": seed["max_soilmoisture"],
            "time_harvest": seed["time_harvest"]
        }
    return None


def find_top_3_seeds(moisture: float, season: str) -> list:
    """Finds top 3 seeds matching both moisture and season constraints."""
    candidates = []

    for seed in list_seeds:
        candidate = evaluate_seed(seed, moisture, season)
        if candidate:
            candidates.append(candidate)

    # Sort candidates by fastest minimum harvest days
    candidates.sort(key=lambda seed: seed["time_harvest"][0])

    return candidates[:3]


def find_seasonal_seeds(season: str) -> list:
    """Finds top 3 seeds based strictly on season, ignoring current moisture."""
    candidates = []

    for seed in list_seeds:
        if is_season_ok(seed, season):
            candidates.append(seed)

    # Sort candidates by fastest minimum harvest days
    candidates.sort(key=lambda seed: seed["time_harvest"][0])

    return candidates[:3]