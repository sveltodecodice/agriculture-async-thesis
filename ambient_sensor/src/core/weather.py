import random

from common.constants import WEATHER_PROBS

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