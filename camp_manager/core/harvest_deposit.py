import json
import os
from datetime import datetime, timezone

# Stored next to core/, e.g. camp_manager/data/harvest_deposit.json
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


def record_harvest(seed_name: str, harvest_date: str = None) -> dict:
    """
    Appends one entry to the harvest deposit log.
    `harvest_date` should be the in-sim date (e.g. "22/11/2026") if you have it;
    falls back to the real-world UTC timestamp if not provided.
    """
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
    return record


def get_harvest_history() -> list:
    """Returns the full harvest log."""
    _ensure_file()
    with open(DEPOSIT_FILE, "r") as f:
        return json.load(f)


def get_harvest_count(seed_name: str = None) -> int:
    """Total harvests logged, optionally filtered by seed name."""
    history = get_harvest_history()
    if seed_name:
        return sum(1 for h in history if h.get("seed") == seed_name)
    return len(history)