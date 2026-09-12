import random

def get_wind_speed(season: str, weather: str) -> float:
    w = str(weather).lower()
    if w in ("rain", "rainy"):
        return round(random.uniform(15.0, 30.0), 1)
    elif w in ("cloudy", "nuvoloso"):
        return round(random.uniform(8.0, 18.0), 1)
    else:
        return round(random.uniform(3.0, 12.0), 1)