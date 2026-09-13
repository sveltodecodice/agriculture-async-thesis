"""Crop metadata used by the UI.

This deliberately stays as plain data: adding a crop should be possible without
understanding the MQTT or HTTP layers.
"""

SEEDS_DATA = [
    {"key": "tomato", "name_it": "Pomodoro", "min_soilmoisture": 0.25, "max_soilmoisture": 0.30, "min_temperature": 18, "max_temperature": 27, "ideal_soil": "Franco", "days": 60, "seasons": ["Primavera", "Estate"]},
    {"key": "zucchini", "name_it": "Zucchine", "min_soilmoisture": 0.26, "max_soilmoisture": 0.31, "min_temperature": 18, "max_temperature": 28, "ideal_soil": "Franco", "days": 50, "seasons": ["Primavera", "Estate"]},
    {"key": "lettuce", "name_it": "Insalata", "min_soilmoisture": 0.28, "max_soilmoisture": 0.33, "min_temperature": 10, "max_temperature": 20, "ideal_soil": "Sabbioso", "days": 30, "seasons": ["Primavera", "Autunno"]},
    {"key": "carrot", "name_it": "Carote", "min_soilmoisture": 0.24, "max_soilmoisture": 0.29, "min_temperature": 15, "max_temperature": 22, "ideal_soil": "Franco-Sabbioso", "days": 70, "seasons": ["Primavera", "Autunno"]},
    {"key": "bean", "name_it": "Fagioli", "min_soilmoisture": 0.25, "max_soilmoisture": 0.30, "min_temperature": 18, "max_temperature": 26, "ideal_soil": "Franco", "days": 60, "seasons": ["Primavera", "Estate"]},
    {"key": "pea", "name_it": "Piselli", "min_soilmoisture": 0.24, "max_soilmoisture": 0.29, "min_temperature": 10, "max_temperature": 18, "ideal_soil": "Franco-Sabbioso", "days": 65, "seasons": ["Primavera", "Autunno", "Inverno"]},
    {"key": "spinach", "name_it": "Spinaci", "min_soilmoisture": 0.30, "max_soilmoisture": 0.35, "min_temperature": 8, "max_temperature": 18, "ideal_soil": "Franco", "days": 40, "seasons": ["Autunno", "Inverno", "Primavera"]},
    {"key": "eggplant", "name_it": "Melanzane", "min_soilmoisture": 0.26, "max_soilmoisture": 0.31, "min_temperature": 20, "max_temperature": 30, "ideal_soil": "Franco-Argilloso", "days": 80, "seasons": ["Primavera", "Estate"]},
    {"key": "bell_pepper", "name_it": "Peperoni", "min_soilmoisture": 0.25, "max_soilmoisture": 0.30, "min_temperature": 20, "max_temperature": 30, "ideal_soil": "Franco-Argilloso", "days": 75, "seasons": ["Primavera", "Estate"]},
    {"key": "cucumber", "name_it": "Cetrioli", "min_soilmoisture": 0.28, "max_soilmoisture": 0.33, "min_temperature": 18, "max_temperature": 28, "ideal_soil": "Franco", "days": 55, "seasons": ["Primavera", "Estate"]},
    {"key": "corn", "name_it": "Mais", "min_soilmoisture": 0.22, "max_soilmoisture": 0.27, "min_temperature": 18, "max_temperature": 30, "ideal_soil": "Franco", "days": 75, "seasons": ["Primavera", "Estate"]},
    {"key": "wheat", "name_it": "Grano", "min_soilmoisture": 0.18, "max_soilmoisture": 0.23, "min_temperature": 10, "max_temperature": 24, "ideal_soil": "Argilloso", "days": 90, "seasons": ["Autunno", "Inverno"]},
    {"key": "basil", "name_it": "Basilico", "min_soilmoisture": 0.25, "max_soilmoisture": 0.30, "min_temperature": 18, "max_temperature": 28, "ideal_soil": "Franco-Sabbioso", "days": 40, "seasons": ["Primavera", "Estate"]},
    {"key": "pumpkin", "name_it": "Zucca", "min_soilmoisture": 0.25, "max_soilmoisture": 0.30, "min_temperature": 18, "max_temperature": 27, "ideal_soil": "Franco", "days": 100, "seasons": ["Primavera", "Estate"]},
    {"key": "cabbage", "name_it": "Cavolo", "min_soilmoisture": 0.27, "max_soilmoisture": 0.32, "min_temperature": 10, "max_temperature": 20, "ideal_soil": "Franco-Argilloso", "days": 85, "seasons": ["Autunno", "Inverno"]},
    {"key": "garlic", "name_it": "Aglio", "min_soilmoisture": 0.18, "max_soilmoisture": 0.23, "min_temperature": 5, "max_temperature": 18, "ideal_soil": "Sabbioso", "days": 180, "seasons": ["Autunno", "Inverno"]},
    {"key": "onion", "name_it": "Cipolla", "min_soilmoisture": 0.20, "max_soilmoisture": 0.25, "min_temperature": 13, "max_temperature": 24, "ideal_soil": "Franco-Sabbioso", "days": 120, "seasons": ["Primavera", "Autunno"]},
    {"key": "strawberry", "name_it": "Fragole", "min_soilmoisture": 0.28, "max_soilmoisture": 0.33, "min_temperature": 15, "max_temperature": 25, "ideal_soil": "Sabbioso", "days": 90, "seasons": ["Primavera", "Autunno"]},
    {"key": "sunflower", "name_it": "Girasole", "min_soilmoisture": 0.18, "max_soilmoisture": 0.23, "min_temperature": 18, "max_temperature": 28, "ideal_soil": "Argilloso", "days": 90, "seasons": ["Primavera", "Estate"]},
    {"key": "arugula", "name_it": "Rucola", "min_soilmoisture": 0.25, "max_soilmoisture": 0.30, "min_temperature": 10, "max_temperature": 22, "ideal_soil": "Franco-Sabbioso", "days": 30, "seasons": ["Primavera", "Autunno"]},
]

CROPS_INFO = {
    seed["name_it"]: {
        "key": seed["key"],
        "threshold": seed["min_soilmoisture"],
        "max_threshold": seed["max_soilmoisture"],
        "ideal_soil": seed["ideal_soil"],
        "days": seed["days"],
        "min_temp": seed["min_temperature"],
        "max_temp": seed["max_temperature"],
        "seasons": seed["seasons"],
    }
    for seed in SEEDS_DATA
}

CROP_KEY_TO_NAME = {}
for seed in SEEDS_DATA:
    CROP_KEY_TO_NAME[seed["key"].lower()] = seed["name_it"]
    CROP_KEY_TO_NAME[seed["name_it"].lower()] = seed["name_it"]
CROP_KEY_TO_NAME["bell pepper"] = "Peperoni"
CROP_KEY_TO_NAME["peperoni"] = "Peperoni"
