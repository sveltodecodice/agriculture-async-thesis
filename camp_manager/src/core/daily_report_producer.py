import json
import os
import logging

from common.constants import DAILY_FARM_REPORT_PATH

logger = logging.getLogger(__name__)


def add_to_daily_report(
    event_type: str, details: str, date_str: str = "01/01/2026", stats: dict = None
):
    logs = []
    if os.path.exists(DAILY_FARM_REPORT_PATH):
        try:
            with open(DAILY_FARM_REPORT_PATH, "r") as f:
                logs = json.load(f)
        except Exception as e:
            logger.error(f"{e}")
            logs = []

    if stats:
        temp = stats.get("temperature", "--")
        weather = stats.get("weather", "Sunny")
        moist = round(stats.get("moisture", 0.0), 1)
        oxy = round(stats.get("oxygenation", 0.0), 1)
        soil_type = stats.get("soil_type", "Loam")
        water_mm = stats.get("water_dispensed_mm", 0.0)
        pump = "ON" if stats.get("irrigation_active") else "OFF"
        plant = stats.get("seed_name") if stats.get("occupied") else "EMPTY"

        details = (
            f"{details} | Temp: {temp}°C | Weather: {weather} | Moist: {moist}% | "
            f"Oxy: {oxy}% | Soil: {soil_type} | Water: {water_mm}mm | Pump: {pump} | Plant: {plant}"
        )

    entry = {
        "date": date_str,
        "event": event_type,
        "details": details,
    }

    logs.append(entry)

    os.makedirs("data", exist_ok=True)
    with open(DAILY_FARM_REPORT_PATH, "w") as f:
        json.dump(logs, f, indent=2)

    return logs


def get_report():
    if not os.path.exists(DAILY_FARM_REPORT_PATH):
        return []
    try:
        with open(DAILY_FARM_REPORT_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"{e}")
        return []


def clear_reports():
    os.makedirs("data", exist_ok=True)
    with open(DAILY_FARM_REPORT_PATH, "w") as f:
        json.dump([], f)
    return []
