import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

import config_loader


def test_yaml_configuration_is_loaded():
    assert config_loader.config_value("farm.fields")

def test_dashboard_environment_overrides_yaml_configuration(monkeypatch):
    monkeypatch.setattr(config_loader,"CONFIG",{"dashboard":{"port":8501}})
    monkeypatch.delenv("PORT",raising=False)
    assert config_loader.env_value("PORT","dashboard.port",8000,int)==8501
    monkeypatch.setenv("PORT","9000")
    assert config_loader.env_value("PORT","dashboard.port",8000,int)==9000
