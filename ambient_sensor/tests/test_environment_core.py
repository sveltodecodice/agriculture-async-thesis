import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

from core.manager import SensorManager
from core.season import get_season

def test_season_mapping_and_invalid_month():
    assert get_season(1)=="winter"
    assert get_season(4)=="spring"
    assert get_season(7)=="summer"
    assert get_season(10)=="autumn"
    try:
        get_season(13)
    except ValueError:
        pass
    else:
        raise AssertionError("Month 13 must be rejected")

def test_sensor_manager_advances_calendar_day():
    manager=SensorManager(day=31,month=1,year=2026)
    manager.update_environment()
    state=manager.get_state()
    assert state["day"]==1
    assert state["month"]==2
    assert state["year"]==2026
    assert state["date"]=="01/02/2026"
    assert state["season"]=="winter"
