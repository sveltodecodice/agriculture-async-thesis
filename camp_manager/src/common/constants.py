from pathlib import Path

from common.config_loader import config_value

# Minimum soil moisture percentage required by crop type
_CROPS = config_value("crops", [])
SEED_TARGETS = {}
for crop in _CROPS:
    if not crop.get("selectable", True):
        continue
    target = round(float(crop.get("min_soilmoisture", 0.18)) * 100, 1)
    SEED_TARGETS[str(crop.get("key", "")).lower()] = target
    if crop.get("name_it"):
        SEED_TARGETS[str(crop["name_it"]).lower()] = target

# Initial state template for monitoring field conditions
DEFAULT_STATE = {
    "occupied": False,
    "empty_days": 0,
    "moisture": float(config_value("defaults.terrain.initial_moisture", 28.0)),
    "oxygenation": float(config_value("defaults.terrain.initial_oxygenation", 70.0)),
    "temperature": float(config_value("defaults.environment.temperature", 20.0)),
    "weather": str(config_value("defaults.environment.weather", "Sunny")),
    "irrigation_active": False,
    "irrigation_pending": False,
    "irrigation_request_id": None,
    "reoxygenation_pending": False,
    "reoxygenation_request_id": None,
    "irrigator_operation": "unknown",
    "season": str(config_value("defaults.environment.season", "winter")),
    "date": str(config_value("simulation.start_date", "01/01/2026")),
    "seed_name": None,
    "min_moisture": 18.0,
    "time_left": 0,
    "harvest_pending": False,
    "soil_type": "Franco",  # observed value will come from Terrain Sensor telemetry
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
