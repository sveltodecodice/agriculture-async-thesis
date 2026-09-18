import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

from core.irrigation import apply_irrigation
from core.soil_type import select_initial_soil
from core.terrain_condition import create_terrain_state, process_terrain_update

def test_random_soil_layout_is_reproducible_and_distinct():
    soils=[select_initial_soil("field_a","random",2026),select_initial_soil("field_b","random",2026),select_initial_soil("field_c","random",2026)]
    assert len(set(soils))==3
    assert soils==[select_initial_soil("field_a","random",2026),select_initial_soil("field_b","random",2026),select_initial_soil("field_c","random",2026)]

def test_irrigation_is_applied_only_when_explicitly_requested():
    assert apply_irrigation(30.0,7.5)==37.5
    assert apply_irrigation(98.0,5.0)==100.0

def test_natural_terrain_update_does_not_mark_irrigation_active():
    state=create_terrain_state(30.0,70.0,"Franco")
    telemetry=process_terrain_update(state,{"temperature":20.0,"rain_mm":0.0,"radiation_wm2":500.0,"wind_kmh":10.0,"date":"02/01/2026"})
    assert telemetry["irrigation_active"] is False
    assert telemetry["water_dispensed_mm"]==0.0
    assert telemetry["date"]=="02/01/2026"
