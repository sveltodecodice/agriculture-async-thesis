"""Local persistence for harvest history records."""

import fcntl
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from common.constants import DATA_OUTPUT_PATH

logger = logging.getLogger(__name__)
LOCK_PATH = f"{DATA_OUTPUT_PATH}.lock"


def _ensure_storage_directory() -> None:
    """Creates the persistence directory when it does not exist."""
    target_dir = os.path.dirname(DATA_OUTPUT_PATH)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)


def _read_history_unlocked() -> List[Dict[str, Any]]:
    """Reads the JSON history while the caller owns the file lock."""
    if not os.path.exists(DATA_OUTPUT_PATH):
        return []

    try:
        with open(DATA_OUTPUT_PATH, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as err:
        logger.error("Failed to read harvest deposit history: %s", err)
        return []


def get_harvest_history() -> List[Dict[str, Any]]:
    """Returns the shared harvest history using a read lock."""
    _ensure_storage_directory()

    with open(LOCK_PATH, "a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle, fcntl.LOCK_SH)
        try:
            return _read_history_unlocked()
        finally:
            fcntl.flock(lock_handle, fcntl.LOCK_UN)


def save_harvest(
    seed_name: str, harvest_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Appends one harvest atomically to the shared JSON history.

    The three Harvester replicas share the same Docker volume. The exclusive
    lock prevents two replicas from performing overlapping read/modify/write
    operations and losing one of the harvest records.
    """
    _ensure_storage_directory()
    timestamp = harvest_date if harvest_date else str(datetime.now())

    with open(LOCK_PATH, "a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle, fcntl.LOCK_EX)
        try:
            history = _read_history_unlocked()
            history.append({"seed": seed_name, "harvested_on": timestamp})

            temporary_path = f"{DATA_OUTPUT_PATH}.tmp"
            with open(temporary_path, "w", encoding="utf-8") as file_handle:
                json.dump(history, file_handle, indent=2)
                file_handle.flush()
                os.fsync(file_handle.fileno())

            os.replace(temporary_path, DATA_OUTPUT_PATH)
            return history
        except PermissionError as err:
            logger.error(
                "Permission denied attempting to write %s: %s", DATA_OUTPUT_PATH, err
            )
            return _read_history_unlocked()
        except OSError as err:
            logger.error("Failed to write harvest deposit: %s", err)
            return _read_history_unlocked()
        finally:
            fcntl.flock(lock_handle, fcntl.LOCK_UN)
