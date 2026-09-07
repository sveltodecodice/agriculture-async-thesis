import json
import os
from datetime import datetime

FILE_PATH = "data/harvest_deposit.json"

def get_harvest_history():
    if not os.path.exists(FILE_PATH):
        os.makedirs("data", exist_ok=True)
        f = open(FILE_PATH, "w")
        json.dump([], f)
        f.close()
        return []

    try:
        f = open(FILE_PATH, "r")
        data = json.load(f)
        f.close()
        return data
    except Exception:
        return []

def save_harvest(seed_name, harvest_date=None):
    if not os.path.exists(FILE_PATH):
        os.makedirs("data", exist_ok=True)
        f = open(FILE_PATH, "w")
        json.dump([], f)
        f.close()

    f = open(FILE_PATH, "r")
    data = json.load(f)
    f.close()

    if harvest_date:
        d = harvest_date
    else:
        d = str(datetime.now())

    item = {"seed": seed_name, "harvested_on": d}
    data.append(item)

    f = open(FILE_PATH, "w")
    json.dump(data, f, indent=2)
    f.close()

    return data