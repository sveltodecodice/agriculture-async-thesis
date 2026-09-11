import json
import os

LOG_FILE = "data/daily_farm_log.json"


def log_event(event_type: str, details: str, date_str: str = "01/01/2026", stats: dict = None):
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except Exception:
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
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

    return logs


def get_logs():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def clear_logs():
    os.makedirs("data", exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump([], f)
    return []