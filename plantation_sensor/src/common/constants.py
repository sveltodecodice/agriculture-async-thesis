"""Application constants and seed parameters for plantation operations."""

from common.config_loader import env_json

_CROPS = env_json("CROPS_JSON", "crops", [])
SEEDS_LST = [
    {
        "name": crop["key"],
        "min_soilmoisture": int(round(float(crop.get("min_soilmoisture", 0.20)) * 100)),
        "max_soilmoisture": int(round(float(crop.get("max_soilmoisture", 0.80)) * 100)),
        "min_temperature": crop.get("min_temperature", 10),
        "max_temperature": crop.get("max_temperature", 30),
        "seasons": crop.get("seasons", []),
        "time_harvest": tuple(crop.get("harvest_time", [crop.get("days", 5), crop.get("days", 5)])),
    }
    for crop in _CROPS
]

DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
