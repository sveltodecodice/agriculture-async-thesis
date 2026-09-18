import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

from common import config_loader


def test_yaml_configuration_is_loaded():
    assert config_loader.config_value("farm.fields")

def test_environment_overrides_yaml_configuration(monkeypatch):
    monkeypatch.setattr(config_loader, "CONFIG", {"mqtt": {"host": "yaml-broker"}})
    monkeypatch.delenv("MQTT_BROKER_HOST", raising=False)
    assert config_loader.env_value("MQTT_BROKER_HOST", "mqtt.host", "default-broker", str) == "yaml-broker"
    monkeypatch.setenv("MQTT_BROKER_HOST", "env-broker")
    assert config_loader.env_value("MQTT_BROKER_HOST", "mqtt.host", "default-broker", str) == "env-broker"
