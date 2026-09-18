"""Application constants and soil factor mappings for terrain operations."""

from common.config_loader import env_json, env_list

SOIL_FACTORS = env_json("SOIL_FACTORS_JSON", "terrain.soil_factors", {
    "sandy":1.10,"sabbioso":1.10,"loam":1.00,"franco":1.00,
    "sandy-loam":1.05,"franco-sabbioso":1.05,"franco sabbioso":1.05,
    "clay-loam":0.95,"franco-argilloso":0.95,"franco argilloso":0.95,
    "clay":0.90,"argilloso":0.90
})
SOIL_TYPES = env_list("SOIL_TYPES", "simulation.soil_layout.available_types", ["Franco","Sabbioso","Franco-Sabbioso","Franco-Argilloso","Argilloso"])
FIELD_ORDER = env_list("CAMP_IDS", "farm.fields", ["field_a","field_b","field_c"])

DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
