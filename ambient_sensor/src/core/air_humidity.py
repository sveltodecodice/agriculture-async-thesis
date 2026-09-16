"""Air humidity and rainfall simulation calculations."""

import random


def get_humidity_air(weather: str) -> float:
    """Calculates outdoor air relative humidity percentage based on weather.

    Args:
        weather (str): Current weather condition.

    Returns:
        float: Relative humidity percentage rounded to 1 decimal place.
    """
    weather_type = str(weather).lower().strip()

    if weather_type in ("rain", "rainy", "pioggia"):
        humidity = random.uniform(78.0, 95.0)
    elif weather_type in ("cloudy", "nuvoloso"):
        humidity = random.uniform(58.0, 82.0)
    else:
        humidity = random.uniform(38.0, 62.0)

    return round(humidity, 1)


def get_rain_mm(weather: str) -> float:
    """Calculates rainfall volume in millimeters based on weather.

    Args:
        weather (str): Current weather condition.

    Returns:
        float: Rainfall volume in mm rounded to 1 decimal place.
    """
    weather_type = str(weather).lower().strip()

    if weather_type in ("rain", "rainy", "pioggia"):
        return round(random.uniform(2.0, 15.0), 1)

    return 0.0
