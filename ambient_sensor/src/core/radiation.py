import random


def get_radiation(season: str, weather: str) -> float:
    base_rad = {
        "spring": 600.0,
        "summer": 900.0,
        "autumn": 400.0,
        "winter": 250.0,
    }.get(season.lower(), 500.0)

    if weather == "Rainy":
        multiplier = random.uniform(0.1, 0.3)
    elif weather == "Cloudy":
        multiplier = random.uniform(0.3, 0.6)
    else:
        multiplier = random.uniform(0.8, 1.1)

    return round(base_rad * multiplier, 0)