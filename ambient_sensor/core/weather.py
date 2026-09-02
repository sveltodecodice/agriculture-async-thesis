import random

RAIN_PROBS = {
    "winter": 0.3,
    "spring": 0.2,
    "summer": 0.1,
    "autumn": 0.3
}

def get_weather_condition(season):
    rain_probability = RAIN_PROBS.get(season, 0.2)
    
    if random.random() < rain_probability :
        return "rain"
    else:
        return "sun"