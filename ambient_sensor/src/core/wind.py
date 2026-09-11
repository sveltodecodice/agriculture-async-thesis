import random


def get_wind_speed(season: str, weather: str) -> float:
    base_speed = {
        "spring": 12.0,
        "summer": 6.0,
        "autumn": 15.0,
        "winter": 10.0,
    }.get(season.lower(), 10.0)

    if weather == "Rainy":
        multiplier = random.uniform(1.5, 2.5)
    elif weather == "Cloudy":
        multiplier = random.uniform(1.0, 1.5)
    else:
        multiplier = random.uniform(0.5, 1.2)

    return round(base_speed * multiplier, 1)