import random

WEATHER_PROBS = {
    "winter": [("sun", 0.6), ("rain", 0.4)],
    "spring": [("sun", 0.7), ("rain", 0.3)],
    "summer": [("sun", 0.8), ("rain", 0.2)],
    "autumn": [("sun", 0.7), ("rain", 0.3)]
}

def get_weather_condition(season):
    conditions = []
    weights = []

    for condition, weight in WEATHER_PROBS[season]:
        conditions.append(condition)
        weights.append(weight)

    return random.choices(conditions, weights=weights)[0]