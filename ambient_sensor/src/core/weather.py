import random

WEATHER_PROBS = {
    "winter": {"rain": 0.3, "cloudy": 0.4, "sun": 0.3},
    "spring": {"rain": 0.2, "cloudy": 0.3, "sun": 0.5},
    "summer": {"rain": 0.1, "cloudy": 0.2, "sun": 0.7},
    "autumn": {"rain": 0.3, "cloudy": 0.4, "sun": 0.3},
}


def get_weather_condition(season: str) -> str:
    if season not in WEATHER_PROBS:
        raise ValueError(f"Invalid season: {season}.")

    probs = WEATHER_PROBS[season]
    r = random.random()

    if r < probs["rain"]:
        return "rain"
    elif r < (probs["rain"] + probs["cloudy"]):
        return "cloudy"

    return "sun"