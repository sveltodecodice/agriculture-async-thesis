import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

from core.plant_conditions import advance_days,check_health,clear_field,create_default_plantation_state,get_growth_percentage,get_growth_stage,seed_planted

def test_seed_planting_and_growth_progress():
    state=create_default_plantation_state()
    seed_planted(state,{"name":"test_crop","min_soilmoisture":20,"max_soilmoisture":40,"min_temperature":10,"max_temperature":30,"seasons":["spring"],"time_harvest":4})
    assert state["occupied"] is True
    assert state["plant_name"]=="Test_crop"
    assert state["time_left"]==4
    advance_days(state,1)
    assert state["time_left"]==3
    assert get_growth_percentage(state)==25.0
    assert get_growth_stage(state)=="VEGETATIVE"

def test_health_and_clear_field():
    state=create_default_plantation_state()
    seed_planted(state,{"name":"test_crop","min_soilmoisture":20,"max_soilmoisture":40,"min_temperature":10,"max_temperature":30,"seasons":["spring"],"time_harvest":4})
    assert check_health(state,25,20,"spring")=="HEALTHY"
    assert "TOO_DRY" in check_health(state,10,20,"spring")
    clear_field(state)
    assert state["occupied"] is False
    assert state["plant_name"] is None
    assert state["time_left"]==0
