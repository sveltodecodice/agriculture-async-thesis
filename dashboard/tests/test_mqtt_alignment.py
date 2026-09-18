import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

import unittest

from config import MQTT_CLIENT_ID, TOPICS
from mqtt_contract import build_command


class MqttAlignmentTests(unittest.TestCase):
    def test_dashboard_subscribes_to_manager_telemetry_contract(self):
        self.assertIn("camp/+/environment/telemetry", TOPICS)
        self.assertIn("camp/+/terrain/telemetry", TOPICS)
        self.assertIn("camp/+/plantation/status", TOPICS)
        self.assertIn("camp/+/system/status", TOPICS)
        self.assertIn("camp/+/irrigator/status", TOPICS)
        self.assertIn("camp/manager/status", TOPICS)

    def test_dashboard_has_unique_client_identifier(self):
        self.assertEqual(MQTT_CLIENT_ID, "smart-farm-dashboard")

    def test_dashboard_commands_match_manager_subscription(self):
        for action in ("plant", "irrigate", "reoxygenate", "clear", "restart"):
            params = {"crop_key": "tomato"} if action == "plant" else {}
            command = build_command("field_a", action, params)
            self.assertTrue(command["topic"].startswith("camp/field_a/camp_manager/cmd/"))

    def test_skip_targets_environment_clock_owner(self):
        command = build_command("field_a", "skip", {"days": 3})
        self.assertEqual(command["topic"], "camp/field_a/environment/cmd/skip")
        self.assertEqual(command["payload"], "3")


if __name__ == "__main__":
    unittest.main()
