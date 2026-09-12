import random

def get_humidity_air(weather: str) -> float:
    w = str(weather).lower()
    if w in ("rain", "rainy", "pioggia"):
        return round(random.uniform(80.0, 95.0), 1)
    elif w in ("cloudy", "nuvoloso"):
        return round(random.uniform(65.0, 80.0), 1)
    else:  # sun / sunny
        return round(random.uniform(40.0, 60.0), 1)


def get_rain_mm(weather: str) -> float:
    w = str(weather).lower()
    if w in ("rain", "rainy", "pioggia"):
        return round(random.uniform(2.0, 15.0), 1)
    return 0.0  # Sia sun che cloudy non producono pioggia