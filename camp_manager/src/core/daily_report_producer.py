import logging
import os
import orjson

from common.constants import DAILY_FARM_REPORT_PATH

logger = logging.getLogger(__name__)


def add_to_daily_report(
    event_type: str, details: str, date_str: str = "01/01/2026", stats: dict = None
) -> list:
    report = []

    # Ensure target directory exists
    dir_path = os.path.dirname(DAILY_FARM_REPORT_PATH.split("/")[0])
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    if os.path.exists(DAILY_FARM_REPORT_PATH):
        try:
            with open(DAILY_FARM_REPORT_PATH, "rb") as f:
                content = f.read()
                if content.strip():
                    report = orjson.loads(content)
        except Exception as e:
            logger.error(f"Error reading daily report file: {e}", exc_info=True)
            report = []

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

    report.append(entry)

    try:
        with open(DAILY_FARM_REPORT_PATH, "wb") as f:
            f.write(orjson.dumps(report, option=orjson.OPT_INDENT_2))
    except Exception as e:
        logger.error(f"Error writing to daily report file: {e}", exc_info=True)

    return report
