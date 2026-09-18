"""Application constants and mapping tables for environment simulation."""

from common.config_loader import env_json

MONTH_TO_SEASON = {1:"winter",2:"winter",3:"spring",4:"spring",5:"spring",6:"summer",7:"summer",8:"summer",9:"autumn",10:"autumn",11:"autumn",12:"winter"}

SEASON_TEMPERATURE_RANGES = env_json("SEASON_TEMPERATURE_RANGES_JSON", "environment.temperature_ranges", {
    "autumn": [16,22], "winter": [12,16], "spring": [20,25], "summer": [28,35]
})
SEASON_TEMPERATURE_RANGES = {key: tuple(value) for key, value in SEASON_TEMPERATURE_RANGES.items()}

SEASON_WEATHER_PROBABILITIES = env_json("SEASON_WEATHER_PROBABILITIES_JSON", "environment.weather_probability", {
    "winter":{"rain":0.3,"cloudy":0.4,"sun":0.3},
    "spring":{"rain":0.2,"cloudy":0.3,"sun":0.5},
    "summer":{"rain":0.1,"cloudy":0.2,"sun":0.7},
    "autumn":{"rain":0.3,"cloudy":0.4,"sun":0.3},
})

SEASON_RADIATION_RANGES = env_json("SEASONS_RADIATION_RANGES_JSON", "environment.radiation_ranges", {
    "summer":[600.0,850.0], "spring":[450.0,650.0], "autumn":[300.0,500.0], "winter":[150.0,300.0]
})
SEASON_RADIATION_RANGES = {key: tuple(value) for key, value in SEASON_RADIATION_RANGES.items()}

DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
