import random

from common.constants import SEASONS_WEATHER_PROBABILITY


def get_weather_condition(season: str) -> str:
    if season not in SEASONS_WEATHER_PROBABILITY:
        raise ValueError(f"Invalid season: {season}.")

    probs = SEASONS_WEATHER_PROBABILITY[season]
    r = random.random()

    if r < probs["rain"]:
        return "rain"
    elif r < (probs["rain"] + probs["cloudy"]):
        return "cloudy"

    return "sun"
