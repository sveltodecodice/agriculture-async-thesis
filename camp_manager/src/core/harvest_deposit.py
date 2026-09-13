import json
import os
from datetime import datetime
import logging

from common.constants import DATA_OUTPUT_PATH

logger = logging.getLogger(__name__)


def get_harvest_history():
    if not os.path.exists(DATA_OUTPUT_PATH):
        os.makedirs("data", exist_ok=True)
        with open(DATA_OUTPUT_PATH, "w") as f:
            json.dump([], f)
        return []

    try:
        with open(DATA_OUTPUT_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"{e}")
        return []


def save_harvest(seed_name: str, harvest_date: str = None) -> list:
    data = get_harvest_history()
    timestamp = harvest_date if harvest_date else str(datetime.now())
    data.append({"seed": seed_name, "harvested_on": timestamp})

    target_dir = os.path.dirname(DATA_OUTPUT_PATH)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    try:
        with open(DATA_OUTPUT_PATH, "w") as file_handle:
            json.dump(data, file_handle, indent=2)
    except PermissionError as err:
        logger.error(
            "Permission denied attempting to write %s: %s", DATA_OUTPUT_PATH, err
        )
    except Exception as err:
        logger.error("Failed to write harvest deposit: %s", err)

    return data
