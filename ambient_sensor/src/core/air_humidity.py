import random


def get_humidity_air(weather: str) -> float:
    """
    Calculates outdoor air humidity using weather-based value ranges.

    Args:
        weather (str): Current weather condition (e.g., 'rain', 'cloudy', 'sunny').

    Returns:
        float: Air relative humidity percentage rounded to 1 decimal place.
    """
    weather_type = str(weather).lower().strip()

    if weather_type in ("rain", "rainy", "pioggia"):
        humidity = random.uniform(78.0, 95.0)
    elif weather_type in ("cloudy", "nuvoloso"):
        humidity = random.uniform(58.0, 82.0)
    else:  # sun / sunny / clear
        humidity = random.uniform(38.0, 62.0)

    return round(humidity, 1)


def get_rain_mm(weather: str) -> float:
    """Calculates rainfall volume in millimeters based on weather conditions.

    Args:
        weather (str): Current weather condition (e.g., 'rain', 'cloudy', 'sunny').

    Returns:
        float: Rainfall in millimeters rounded to 1 decimal place.
    """
    weather_type = str(weather).lower().strip()

    if weather_type in ("rain", "rainy", "pioggia"):
        return round(random.uniform(2.0, 15.0), 1)

    return 0.0
