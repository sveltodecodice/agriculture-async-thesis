KNOWN_CAMPS = ["campo_1", "campo_2", "campo_3"]

SEED_TARGETS = {
    "wheat": 18.0,
    "grano": 18.0,
    "corn": 22.0,
    "mais": 22.0,
    "potato": 23.0,
    "patate": 23.0,
    "carrot": 24.0,
    "carote": 24.0,
    "tomato": 25.0,
    "pomodoro": 25.0,
    "zucchini": 26.0,
    "zucchine": 26.0,
    "lettuce": 28.0,
    "insalata": 28.0,
    "spinach": 30.0,
    "spinaci": 30.0,
    "sunflower": 20.0,
    "girasole": 20.0,
}

DEFAULT_STATE = {
    "occupied": False,
    "empty_days": 0,
    "moisture": 28.0,
    "oxygenation": 70.0,
    "temperature": 20,
    "weather": "Sunny",
    "irrigation_active": False,
    "season": "winter",
    "date": "01/01/2026",
    "seed_name": None,
    "min_moisture": 18.0,
    "time_left": 0,
    "harvest_pending": False,
    "soil_type": "Franco",
    "water_dispensed_mm": 0.0,
}

OUTPUT_DIRECTORY = "data/"
DATA_OUTPUT_FILENAME = "harvest_deposit.json"
DATA_OUTPUT_PATH = OUTPUT_DIRECTORY + DATA_OUTPUT_FILENAME

DAILY_FARM_REPORT_FILENAME = "daily_farm_log.json"
DAILY_FARM_REPORT_PATH = OUTPUT_DIRECTORY + DAILY_FARM_REPORT_FILENAME

DEFAULT_FORMAT = f" %(asctime)s | " "%(levelname)s | " "%(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
