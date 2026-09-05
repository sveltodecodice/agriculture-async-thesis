import json
import os
from datetime import datetime, timezone

DEPOSIT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "harvest_deposit.json",
)

def _ensure_file():
    os.makedirs(os.path.dirname(DEPOSIT_FILE), exist_ok=True)
    if not os.path.exists(DEPOSIT_FILE):
        with open(DEPOSIT_FILE, "w") as f:
            json.dump([], f)

async def record_harvest(seed_name: str, harvest_date: str = None, mqtt_client = None) -> dict:
    if not seed_name:
        print("[DEPOSIT] Skipped record: no seed name provided.", flush=True)
        return {}

    _ensure_file()

    record = {
        "seed": seed_name,
        "harvested_on": harvest_date or datetime.now(timezone.utc).isoformat(),
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(DEPOSIT_FILE, "r") as f:
        data = json.load(f)

    data.append(record)

    with open(DEPOSIT_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[DEPOSIT] Recorded harvest -> {record}", flush=True)

    # Automatically notify MQTT (and Node-RED) of the new harvest
    if mqtt_client:
        try:
            payload = f"🌾 Last Harvested: {seed_name.upper()} on {harvest_date or 'Today'}"
            await mqtt_client.publish("camp/harvest_deposit", payload)
        except Exception as e:
            print(f"[DEPOSIT ERROR] Failed to publish MQTT harvest event: {e}", flush=True)

    return record

def get_harvest_history() -> list:
    _ensure_file()
    with open(DEPOSIT_FILE, "r") as f:
        return json.load(f)

def get_harvest_count(seed_name: str = None) -> int:
    history = get_harvest_history()
    if seed_name:
        return sum(1 for h in history if h.get("seed") == seed_name)
    return len(history)