from common.config_loader import env_json

SEEDS_DATA = [crop for crop in env_json("CROPS_JSON", "crops", []) if crop.get("selectable", True)]

SEEDS_LST = [
    {
        "name": seed["key"],
        "name_it": seed.get("name_it", seed["key"].capitalize()),
        "min_soilmoisture": int(round(float(seed["min_soilmoisture"]) * 100)),
        "max_soilmoisture": int(round(float(seed["max_soilmoisture"]) * 100)),
        "min_temperature": seed["min_temperature"],
        "max_temperature": seed["max_temperature"],
        "ideal_soil": seed.get("ideal_soil"),
        "time_harvest": tuple(seed.get("harvest_time", [seed["days"], seed["days"] + 20])),
        "seasons": seed.get("seasons", []),
    }
    for seed in SEEDS_DATA
]
