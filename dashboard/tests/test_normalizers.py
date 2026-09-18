import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

import unittest

from normalizers import moisture_fraction, plantation_from_payload


class NormalizerTests(unittest.TestCase):
    def test_moisture_accepts_percent_or_fraction(self):
        self.assertEqual(moisture_fraction(25), 0.25)
        self.assertEqual(moisture_fraction(0.25), 0.25)

    def test_new_plantation_shape(self):
        result = plantation_from_payload({
            "camp_availability": True,
            "status_detail": {
                "plant_name": "tomato",
                "time_left": 12,
                "growth_percentage": 80,
                "growth_stage": "FRUITING",
                "health": "HEALTHY",
                "min_soilmoisture": 25,
            },
        })
        self.assertTrue(result["occupied"])
        self.assertEqual(result["crop"], "Pomodoro")
        self.assertEqual(result["min_moisture"], 0.25)
        self.assertEqual(result["max_moisture"], 0.30)
        self.assertEqual(result["min_temperature"], 18)
        self.assertEqual(result["max_temperature"], 27)
        self.assertEqual(result["ideal_soil"], "Franco")

    def test_spinach_metadata_is_available_for_telemetry_assessment(self):
        result = plantation_from_payload({
            "camp_availability": True,
            "status_detail": {
                "plant_name": "spinach",
                "time_left": 3,
                "growth_percentage": 91,
                "growth_stage": "MATURING",
                "health": "HEALTHY",
            },
        })
        self.assertEqual(result["crop"], "Spinaci")
        self.assertEqual(result["min_moisture"], 0.30)
        self.assertEqual(result["max_moisture"], 0.35)
        self.assertEqual(result["min_temperature"], 8)
        self.assertEqual(result["max_temperature"], 18)


if __name__ == "__main__":
    unittest.main()
