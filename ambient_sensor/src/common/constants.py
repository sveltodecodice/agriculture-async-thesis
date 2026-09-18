"""Application constants and mapping tables for environment simulation."""

from common.config_loader import env_json

MONTH_NUM_SEASON_MAP = {1:"winter",2:"winter",3:"spring",4:"spring",5:"spring",6:"summer",7:"summer",8:"summer",9:"autumn",10:"autumn",11:"autumn",12:"winter"}

SEASONS_TEMP_RANGES = env_json("SEASONS_TEMP_RANGES_JSON", "environment.temperature_ranges", {
    "autumn": [16,22], "winter": [12,16], "spring": [20,25], "summer": [28,35]
})
SEASONS_TEMP_RANGES = {key: tuple(value) for key, value in SEASONS_TEMP_RANGES.items()}

SEASONS_WEATHER_PROBABILITY = env_json("SEASONS_WEATHER_PROBABILITY_JSON", "environment.weather_probability", {
    "winter":{"rain":0.3,"cloudy":0.4,"sun":0.3},
    "spring":{"rain":0.2,"cloudy":0.3,"sun":0.5},
    "summer":{"rain":0.1,"cloudy":0.2,"sun":0.7},
    "autumn":{"rain":0.3,"cloudy":0.4,"sun":0.3},
})

SEASONS_RAD_DEFAULT = env_json("SEASONS_RADIATION_RANGES_JSON", "environment.radiation_ranges", {
    "summer":[600.0,850.0], "spring":[450.0,650.0], "autumn":[300.0,500.0], "winter":[150.0,300.0]
})
SEASONS_RAD_DEFAULT = {key: tuple(value) for key, value in SEASONS_RAD_DEFAULT.items()}

DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
