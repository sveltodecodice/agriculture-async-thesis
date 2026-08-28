import random

SEASON_RANGES = { "autumn": (16,22), "winter": (12, 16), "spring": (20,25), "summer": (28, 35)}

def get_temperature(season):
    min_t, max_t = SEASON_RANGES[season]
    return random.randint(min_t, max_t)