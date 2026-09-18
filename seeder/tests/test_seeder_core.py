import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

import pytest
from core.seeder import start_seeding

def test_string_seed_command_is_normalized():
    assert start_seeding(" tomato ")=={"name":"tomato"}

def test_dictionary_seed_command_preserves_payload():
    result=start_seeding({"seed":"carrot","source":"manual"})
    assert result["name"]=="carrot"
    assert result["source"]=="manual"

def test_invalid_seed_command_is_rejected():
    with pytest.raises(ValueError):
        start_seeding("")
