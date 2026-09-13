import random


def get_wind_speed(season: str, weather: str) -> float:
    """
    Calculates wind speed in km/h based on weather conditions.

    Args:
        season (str): Current season (e.g., 'summer', 'winter'). Retained for
            interface consistency.
        weather (str): Current weather condition (e.g., 'rain', 'cloudy', 'sun').

    Returns:
        float: Calculated wind speed in km/h.
    """
    weather_type = str(weather).lower().strip()

    if weather_type in ("rain", "rainy", "pioggia"):
        wind_speed = random.uniform(15.0, 30.0)
    elif weather_type in ("cloudy", "nuvoloso"):
        wind_speed = random.uniform(8.0, 18.0)
    else:  # sun / sunny / clear
        wind_speed = random.uniform(3.0, 12.0)

    return round(wind_speed, 1)