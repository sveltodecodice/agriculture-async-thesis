"""Application constants and file path configurations for harvester operations."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIRECTORY = BASE_DIR / "data"
DATA_OUTPUT_PATH = str(OUTPUT_DIRECTORY / "harvest_deposit.json")

DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
