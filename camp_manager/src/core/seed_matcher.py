from common.seeds import SEEDS_LST

def evaluate_season_ok(seed: dict, season: str) -> bool:
    if not season:
        return False
    return season.lower() in [s.lower() for s in seed.get("seasons", [])]

def evaluate_moisture_ok(seed: dict, moisture: float) -> bool:
    return seed["min_soilmoisture"] <= moisture <= seed["max_soilmoisture"]

def evaluate_seed(seed: dict, moisture: float, season: str) -> dict:
    if evaluate_season_ok(seed, season) and evaluate_moisture_ok(seed, moisture):
        return {
            "name": seed["name"],
            "min_soilmoisture": seed["min_soilmoisture"],
            "max_soilmoisture": seed["max_soilmoisture"],
            "time_harvest": seed["time_harvest"]
        }
    return None

def find_top_3_seeds(moisture, season):
    # Filter by season first
    seasonal_matches = [s for s in SEEDS_LST if evaluate_season_ok(s, season)]
    
    # Fall back to full database if fewer than 3 strict season matches are found
    candidate_list = seasonal_matches if len(seasonal_matches) >= 3 else SEEDS_LST
    
    # Sort candidates by soil moisture proximity
    sorted_seeds = sorted(candidate_list, key=lambda s: abs(s.get("min_soilmoisture", 20.0) - moisture))
    return sorted_seeds[:3]