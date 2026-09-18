import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

import json
import unittest

from mqtt_contract import build_command


class MqttContractTests(unittest.TestCase):
    def test_plant_goes_through_camp_manager_and_seeder(self):
        command = build_command("field_a", "plant", {"crop_key": "tomato"})
        self.assertEqual(command["topic"], "camp/field_a/camp_manager/cmd/plant")
        self.assertEqual(json.loads(command["payload"]), {"seed": "tomato"})
        self.assertEqual(command["target_service"], "Camp Manager -> Seeder")

    def test_irrigation_goes_through_camp_manager_and_irrigator(self):
        command = build_command("field_b", "irrigate", {})
        self.assertEqual(command["topic"], "camp/field_b/camp_manager/cmd/irrigate")
        self.assertEqual(command["target_service"], "Camp Manager -> Irrigator")

    def test_reoxygenation_goes_through_camp_manager_and_irrigator(self):
        command = build_command("field_c", "reoxygenate", {})
        self.assertEqual(command["topic"], "camp/field_c/camp_manager/cmd/reoxygenate")
        self.assertEqual(command["target_service"], "Camp Manager -> Irrigator")

    def test_clear_and_restart_target_manager(self):
        self.assertEqual(build_command("field_a", "clear", {})["topic"], "camp/field_a/camp_manager/cmd/clear")
        self.assertEqual(build_command("field_a", "restart", {})["topic"], "camp/field_a/camp_manager/cmd/restart")

    def test_skip_remains_environment_clock_command(self):
        command = build_command("field_a", "skip", {"days": 2})
        self.assertEqual(command["topic"], "camp/field_a/environment/cmd/skip")
        self.assertEqual(command["payload"], "2")
        self.assertEqual(command["target_service"], "Ambient Sensor")


if __name__ == "__main__":
    unittest.main()
