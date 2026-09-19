"""Small YAML + environment configuration loader.

Precedence: environment variable -> farm.yaml -> code default.

"""

import json
import os
from pathlib import Path

import yaml


def load_config() -> dict:
    path = Path(os.getenv("FARM_CONFIG", "/app/config/farm.yaml"))
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML configuration: {path}")
    return data


CONFIG = load_config()


def config_value(path: str, default=None):
    value = CONFIG
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def env_value(name: str, path: str, default=None, cast=None):
    raw = os.getenv(name)
    value = raw if raw not in (None, "") else config_value(path, default)
    if cast is None or value is None:
        return value
    if cast is bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
    return cast(value)



def env_json(name: str, path: str, default=None):
    raw = os.getenv(name)
    if raw not in (None, ""):
        return json.loads(raw)
    return config_value(path, default)

