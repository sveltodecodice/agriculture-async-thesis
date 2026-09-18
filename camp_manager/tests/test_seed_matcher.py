import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

from core.seed_matcher import evaluate_soil_ok,find_top_3_seeds

def test_soil_labels_are_normalized():
    assert evaluate_soil_ok({"ideal_soil":"Franco-Sabbioso"},"franco sabbioso") is True

def test_season_is_first_priority():
    candidates=find_top_3_seeds(28.0,"summer","Argilloso")
    assert all("summer" in [s.lower() for s in seed["seasons"]] for seed in candidates)

def test_soil_is_second_priority():
    candidates=find_top_3_seeds(28.0,"summer","Franco-Argilloso")
    assert candidates[0]["ideal_soil"].lower()=="franco-argilloso"
