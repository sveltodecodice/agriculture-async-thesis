import random

def get_humidity_air(weather: str) -> float:
    if weather == "Rainy":
        return round(random.uniform(75.0, 95.0), 1)
    elif weather == "Cloudy":
        return round(random.uniform(60.0, 75.0), 1)
    return round(random.uniform(40.0, 60.0), 1)

def get_rain_mm(weather: str) -> float:
    return round(random.uniform(2.0, 18.0), 1) if weather == "Rainy" else 0.0