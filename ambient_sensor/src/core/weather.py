"""Weather condition determination logic."""

import random

from common.constants import SEASON_WEATHER_PROBABILITIES


def get_weather_condition(season: str) -> str:
    """Determines a weather condition based on seasonal probability distributions.

    Args:
        season (str): Target season name.

    Returns:
        str: Selected weather condition ('rain', 'cloudy', or 'sun').

    Raises:
        ValueError: If season is not present in configuration.
    """
    season_key = str(season).lower().strip()

    if season_key not in SEASON_WEATHER_PROBABILITIES:
        raise ValueError(f"Invalid season: {season}.")

    weather_probabilities = SEASON_WEATHER_PROBABILITIES[season_key]
    random_value = random.random()

    rain_threshold = weather_probabilities["rain"]
    cloudy_threshold = rain_threshold + weather_probabilities["cloudy"]

    if random_value < rain_threshold:
        return "rain"
    if random_value < cloudy_threshold:
        return "cloudy"

    return "sun"
