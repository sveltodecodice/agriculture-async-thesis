import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

import pytest
from core.irrigator import start_irrigation,start_reoxygenation

def test_irrigation_accepts_percentage_amount():
    result=start_irrigation({"amount_pct":7.5})
    assert result["amount_pct"]==7.5
    assert result["amount"]==7.5

def test_irrigation_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        start_irrigation({"amount_pct":0})

def test_reoxygenation_uses_requested_target():
    assert start_reoxygenation(95.0)=={"oxygenation":95.0}
