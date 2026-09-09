import json
import os
from datetime import datetime

FILE_PATH = "data/harvest_deposit.json"

def get_harvest_history():
    if not os.path.exists(FILE_PATH):
        os.makedirs("data", exist_ok=True)
        with open(FILE_PATH, "w") as f:
            json.dump([], f)
        return []

    try:
        with open(FILE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_harvest(seed_name, harvest_date=None):
    data = get_harvest_history()

    d = harvest_date if harvest_date else str(datetime.now())
    data.append({"seed": seed_name, "harvested_on": d})

    os.makedirs("data", exist_ok=True)
    with open(FILE_PATH, "w") as f:
        json.dump(data, f, indent=2)

    return data