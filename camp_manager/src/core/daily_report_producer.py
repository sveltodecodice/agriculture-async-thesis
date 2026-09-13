"""Daily farm log producer module.

Appends event records and environmental statistics to a persistent JSON log file.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import orjson
from common.constants import DAILY_FARM_REPORT_PATH

logger = logging.getLogger(__name__)


def add_to_daily_report(
    event_type: str,
    details: str,
    date_str: str = "01/01/2026",
    stats: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Appends a new event record to the daily farm log JSON report.

    Args:
        event_type (str): Type identifier for the logged event (e.g., 'AUTO_PLANT').
        details (str): Human-readable event description.
        date_str (str, optional): Date string formatted as DD/MM/YYYY. Defaults to "01/01/2026".
        stats (Optional[Dict[str, Any]], optional): Dictionary of current camp stats.
            Defaults to None.

    Returns:
        List[Dict[str, Any]]: Updated list of all daily report entries.
    """
    report: List[Dict[str, Any]] = []

    target_dir = os.path.dirname(DAILY_FARM_REPORT_PATH)
    if target_dir:
        try:
            os.makedirs(target_dir, exist_ok=True)
        except PermissionError as error:
            logger.error(
                "Permission denied creating directory %s: %s", target_dir, error
            )

    if os.path.exists(DAILY_FARM_REPORT_PATH):
        try:
            with open(DAILY_FARM_REPORT_PATH, "rb") as file_handle:
                content = file_handle.read()
                if content.strip():
                    report = orjson.loads(content)
        except PermissionError as error:
            logger.error(
                "Permission denied reading daily report file %s: %s",
                DAILY_FARM_REPORT_PATH,
                error,
            )
        except Exception as error:
            logger.error("Error reading daily report file: %s", error, exc_info=True)
            report = []

    if stats:
        temperature = stats.get("temperature", "--")
        weather = stats.get("weather", "Sunny")
        moisture = round(float(stats.get("moisture", 0.0)), 1)
        oxygenation = round(float(stats.get("oxygenation", 0.0)), 1)
        soil_type = stats.get("soil_type", "Loam")
        water_dispensed_mm = stats.get("water_dispensed_mm", 0.0)
        pump_status = "ON" if stats.get("irrigation_active") else "OFF"
        plant_name = stats.get("seed_name") if stats.get("occupied") else "EMPTY"
        growth_stage = stats.get("growth_stage", "EMPTY")
        health = stats.get("health", "FIELD IS EMPTY")

        details = (
            f"{details} | Temp: {temperature}°C | Weather: {weather} | "
            f"Moist: {moisture}% | Oxy: {oxygenation}% | Soil: {soil_type} | "
            f"Water: {water_dispensed_mm}mm | Pump: {pump_status} | "
            f"Plant: {plant_name} | Stage: {growth_stage} | Health: {health}"
        )

    entry = {
        "date": date_str,
        "event": event_type,
        "details": details,
    }

    report.append(entry)

    try:
        with open(DAILY_FARM_REPORT_PATH, "wb") as file_handle:
            file_handle.write(orjson.dumps(report, option=orjson.OPT_INDENT_2))
    except PermissionError as error:
        logger.error(
            "Permission denied writing daily report file %s: %s",
            DAILY_FARM_REPORT_PATH,
            error,
        )
    except Exception as error:
        logger.error("Error writing to daily report file: %s", error, exc_info=True)

    return report
