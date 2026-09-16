"""Local persistence for harvest history records."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from common.constants import DATA_OUTPUT_PATH

logger = logging.getLogger(__name__)


def get_harvest_history() -> List[Dict[str, Any]]:
    """Retrieves existing harvest records from local persistent JSON storage.

    Returns:
        List[Dict[str, Any]]: List of historical harvest records.
    """
    target_dir = os.path.dirname(DATA_OUTPUT_PATH)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    if not os.path.exists(DATA_OUTPUT_PATH):
        try:
            with open(DATA_OUTPUT_PATH, "w", encoding="utf-8") as file_handle:
                json.dump([], file_handle)
        except Exception as err:
            logger.error("Failed to initialize harvest deposit file: %s", err)
        return []

    try:
        with open(DATA_OUTPUT_PATH, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except Exception as err:
        logger.error("Failed to read harvest deposit history: %s", err)
        return []


def save_harvest(
    seed_name: str, harvest_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Appends a new harvest event to persistent storage and returns updated history.

    Args:
        seed_name (str): Name of the harvested seed type.
        harvest_date (Optional[str]): Formatted harvest timestamp or None for current time.

    Returns:
        List[Dict[str, Any]]: Updated complete list of harvest records.
    """
    history = get_harvest_history()
    timestamp = harvest_date if harvest_date else str(datetime.now())
    history.append({"seed": seed_name, "harvested_on": timestamp})

    target_dir = os.path.dirname(DATA_OUTPUT_PATH)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    try:
        with open(DATA_OUTPUT_PATH, "w", encoding="utf-8") as file_handle:
            json.dump(history, file_handle, indent=2)
    except PermissionError as err:
        logger.error(
            "Permission denied attempting to write %s: %s", DATA_OUTPUT_PATH, err
        )
    except Exception as err:
        logger.error("Failed to write harvest deposit: %s", err)

    return history
