import random

from common.constants import SEASONS_DEFAULT


def get_radiation(season: str, weather: str) -> float:
    w = str(weather).lower()
    if w in ("rain", "rainy", "pioggia"):
        return round(random.uniform(50.0, 150.0), 1)
    elif w in ("cloudy", "nuvoloso"):
        return round(random.uniform(150.0, 350.0), 1)
    else:  # sun / sunny
        low, high = SEASONS_DEFAULT.get(season.lower(), (300.0, 500.0))
        return round(random.uniform(low, high), 1)
