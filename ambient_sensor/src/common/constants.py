KNOWN_CAMPS = ["campo_1", "campo_2", "campo_3"]

SEASONS_MAP = {
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
    12: "winter",
}

SEASON_RANGES = {
    "autumn": (16, 22),
    "winter": (12, 16),
    "spring": (20, 25),
    "summer": (28, 35),
}

WEATHER_PROBS = {
    "winter": {"rain": 0.3, "cloudy": 0.4, "sun": 0.3},
    "spring": {"rain": 0.2, "cloudy": 0.3, "sun": 0.5},
    "summer": {"rain": 0.1, "cloudy": 0.2, "sun": 0.7},
    "autumn": {"rain": 0.3, "cloudy": 0.4, "sun": 0.3},
}


SEASONS_DEFAULT = {
    "summer": (600.0, 850.0),
    "spring": (450.0, 650.0),
    "autumn": (300.0, 500.0),
    "winter": (150.0, 300.0),
}

DEFAULT_FORMAT = f" %(asctime)s | " "%(levelname)s | " "%(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
