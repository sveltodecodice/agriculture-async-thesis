import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

import pytest
from core.harvester import start_harvesting

def test_harvest_command_is_normalized():
    assert start_harvesting({"name":"tomato","date":"10/09/2026"})=={"seed":"tomato","date":"10/09/2026"}

def test_harvest_requires_seed_identifier():
    with pytest.raises(ValueError):
        start_harvesting({"date":"10/09/2026"})

def test_harvest_requires_dictionary_payload():
    with pytest.raises(ValueError):
        start_harvesting("tomato")
