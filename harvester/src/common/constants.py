from pathlib import Path

# Fix per Permission Error 13
BASE_DIR = Path(__file__).resolve().parent.parent.parent

OUTPUT_DIRECTORY = BASE_DIR / "data"
DATA_OUTPUT_PATH = str(OUTPUT_DIRECTORY / "harvest_deposit.json")
DAILY_FARM_REPORT_PATH = str(OUTPUT_DIRECTORY / "daily_farm_log.json")

DEFAULT_FORMAT = f" %(asctime)s | " "%(levelname)s | " "%(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"