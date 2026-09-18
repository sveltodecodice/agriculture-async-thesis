from config_loader import env_json

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

CROPS_INFO = {
    seed.get("name_it", seed["key"].capitalize()): {
        "key": seed["key"],
        "threshold": float(seed["min_soilmoisture"]),
        "max_threshold": float(seed["max_soilmoisture"]),
        "ideal_soil": seed.get("ideal_soil"),
        "days": seed["days"],
        "min_temp": seed["min_temperature"],
        "max_temp": seed["max_temperature"],
        "seasons": seed.get("seasons", []),
    }
    for seed in SEEDS_DATA
}

CROP_KEY_TO_NAME = {}
for seed in SEEDS_DATA:
    display_name = seed.get("name_it", seed["key"].capitalize())
    CROP_KEY_TO_NAME[seed["key"].lower()] = display_name
    CROP_KEY_TO_NAME[display_name.lower()] = display_name
CROP_KEY_TO_NAME["bell pepper"] = "Peperoni"
CROP_KEY_TO_NAME["peperoni"] = "Peperoni"
