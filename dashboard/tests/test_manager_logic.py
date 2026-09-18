import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

import unittest

from manager_logic import manager_policy, top_seed_candidates
from seeds import CROPS_INFO


class ManagerLogicTests(unittest.TestCase):
    def test_seed_catalog_matches_manager_and_contains_olive(self):
        self.assertIn("Oliva", CROPS_INFO)
        self.assertEqual(CROPS_INFO["Oliva"]["key"], "olive")

    def test_seed_ranking_uses_season_soil_and_moisture(self):
        candidates = top_seed_candidates(25.0, "summer", "Franco-Sabbioso")
        self.assertEqual(len(candidates), 3)
        self.assertTrue(all("key" in item for item in candidates))
        self.assertTrue(candidates[0]["season_match"])
        self.assertTrue(candidates[0]["soil_match"])
        self.assertEqual(candidates[0]["distance_from_current_pct"], 0.0)

    def test_soil_compatibility_has_priority_inside_same_season(self):
        candidates = top_seed_candidates(28.0, "summer", "Franco-Argilloso")
        self.assertTrue(candidates[0]["season_match"])
        self.assertTrue(candidates[0]["soil_match"])
        self.assertIn(candidates[0]["key"], {"eggplant", "bell_pepper"})

    def test_irrigation_formula_matches_manager(self):
        camp = {
            "environment": {"season": "summer"},
            "terrain": {"soil_moisture": 0.20, "oxygenation": 70, "soil_type": "Franco", "irrigation_active": False},
            "plantation": {"occupied": True, "min_moisture": 0.25, "time_left": 10},
        }
        policy = manager_policy(camp)
        self.assertEqual(policy["irrigation"]["target_min_pct"], 25.0)
        self.assertEqual(policy["irrigation"]["target_after_pct"], 30.0)
        self.assertEqual(policy["irrigation"]["needed_water_pct"], 10.0)
        self.assertTrue(policy["irrigation"]["automatic_required"])

    def test_reoxygenation_and_harvest_thresholds(self):
        camp = {
            "environment": {"season": "spring"},
            "terrain": {"soil_moisture": 0.30, "oxygenation": 29.9, "soil_type": "Franco", "irrigation_active": False},
            "plantation": {"occupied": True, "min_moisture": 0.25, "time_left": 0},
        }
        policy = manager_policy(camp)
        self.assertTrue(policy["oxygenation"]["automatic_required"])
        self.assertTrue(policy["harvest"]["automatic_required"])


if __name__ == "__main__":
    unittest.main()
