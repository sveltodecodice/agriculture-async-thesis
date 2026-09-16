from pathlib import Path

# Minimum soil moisture percentage required by crop type
SEED_TARGETS = {
    "wheat": 18.0,
    "grano": 18.0,
    "corn": 22.0,
    "mais": 22.0,
    "potato": 25.0,
    "patate": 25.0,
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
    "sunflower": 18.0,
    "girasole": 18.0,
}

# Initial state template for monitoring field conditions
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
    "growth_percentage": 0.0,
    "growth_stage": "EMPTY",
    "health": "FIELD IS EMPTY",
    "seeding_pending": False,
}

# File paths for storing project outputs and logs
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIRECTORY = BASE_DIR / "data"
DATA_OUTPUT_PATH = str(OUTPUT_DIRECTORY / "harvest_deposit.json")
DAILY_FARM_REPORT_PATH = str(OUTPUT_DIRECTORY / "daily_farm_log.json")

# Standard logging formats
DEFAULT_FORMAT = " %(asctime)s | %(levelname)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# MQTT Topic Templates
TOPIC_SEEDER_PLANT = "camp/{camp_id}/seeder/cmd/plant"
TOPIC_HARVESTER_HARVEST = "camp/{camp_id}/harvester/cmd/harvest"
TOPIC_IRRIGATOR_IRRIGATE = "camp/{camp_id}/irrigator/cmd/irrigate"
TOPIC_IRRIGATOR_REOXYGENATE = "camp/{camp_id}/irrigator/cmd/reoxygenate"
TOPIC_PLANTATION_CLEARED = "camp/{camp_id}/plantation/event/cleared"
TOPIC_SYSTEM_STATUS = "camp/{camp_id}/system/status"
