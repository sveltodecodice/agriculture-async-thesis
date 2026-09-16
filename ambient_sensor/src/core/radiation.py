"""Solar radiation simulation calculations."""

import random

from common.constants import SEASONS_RAD_DEFAULT


def get_radiation(season: str, weather: str) -> float:
    """Calculates solar radiation in W/m² using seasonal ranges and weather.

    Args:
        season (str): Current target season.
        weather (str): Current weather condition.

    Returns:
        float: Solar radiation in W/m² rounded to 1 decimal place.
    """
    season_key = str(season).lower().strip()
    weather_type = str(weather).lower().strip()

    low, high = SEASONS_RAD_DEFAULT.get(season_key, (300.0, 500.0))
    base_radiation = random.uniform(low, high)

    if weather_type in ("rain", "rainy", "pioggia"):
        attenuation_factor = random.uniform(0.15, 0.30)
    elif weather_type in ("cloudy", "nuvoloso"):
        attenuation_factor = random.uniform(0.35, 0.60)
    else:
        attenuation_factor = random.uniform(0.90, 1.0)

    return round(base_radiation * attenuation_factor, 1)
