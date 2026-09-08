import json
import os

LOG_FILE = "data/daily_farm_log.json"

def log_event(event_type: str, details: str, date_str: str = "01/01/2026", stats: dict = None):
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            f = open(LOG_FILE, "r")
            logs = json.load(f)
            f.close()
        except Exception:
            logs = []

    # Inject all requested telemetry variables into the details string
    if stats:
        temp = stats.get('temperature', '--')
        weather = stats.get('weather', 'Sunny')
        moist = round(stats.get('moisture', 0.0), 1)
        oxy = round(stats.get('oxygenation', 0.0), 1)
        pump = "ON" if stats.get('irrigation_active') else "OFF"
        plant = stats.get('seed_name') if stats.get('occupied') else 'EMPTY'
        
        details = f"{details} | Temp: {temp}°C | Weather: {weather} | Moist: {moist}% | Oxy: {oxy}% | Pump: {pump} | Plant: {plant}"

    entry = {
        "date": date_str,
        "event": event_type,
        "details": details
    }

    logs.append(entry)

    os.makedirs("data", exist_ok=True)
    f = open(LOG_FILE, "w")
    json.dump(logs, f, indent=2)
    f.close()

    return logs

def get_logs():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        f = open(LOG_FILE, "r")
        logs = json.load(f)
        f.close()
        return logs
    except Exception:
        return []

def clear_logs():
    os.makedirs("data", exist_ok=True)
    f = open(LOG_FILE, "w")
    json.dump([], f)
    f.close()
    return []