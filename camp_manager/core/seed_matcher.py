from core.seeds import list_seeds


def evaluate_season_ok(seed: dict, season: str) -> bool:
    if not season:
        return False
    else:
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


def find_top_3_seeds(moisture: float, season: str) -> list:
    top3_candidates = []

    for seed in list_seeds:
        candidate = evaluate_seed(seed, moisture, season)
        if candidate:
            top3_candidates.append(candidate)

    top3_candidates.sort(key=lambda seed: seed["time_harvest"][0])
    return top3_candidates[:3]
