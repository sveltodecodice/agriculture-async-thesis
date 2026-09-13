import random

from common.constants import SEASONS_WEATHER_PROBABILITY


def get_weather_condition(season: str) -> str:
    """
    Determines a weather condition based on seasonal probabilities.

    Args:
        season (str): Name of the target season (e.g., 'spring', 'summer').

    Returns:
        str: Selected weather condition ('rain', 'cloudy', or 'sun').

    Raises:
        ValueError: If the provided season key is not present in the map.
    """
    season_key = str(season).lower().strip()

    if season_key not in SEASONS_WEATHER_PROBABILITY:
        raise ValueError(f"Invalid season: {season}.")

    weather_probabilities = SEASONS_WEATHER_PROBABILITY[season_key]
    random_value = random.random()

    rain_threshold = weather_probabilities["rain"]
    cloudy_threshold = rain_threshold + weather_probabilities["cloudy"]

    if random_value < rain_threshold:
        return "rain"
    if random_value < cloudy_threshold:
        return "cloudy"

    return "sun"
