import os
import sys
from pathlib import Path

sys.path.append("src")

LOCAL_CONFIG = Path("../config/farm.yaml")
if LOCAL_CONFIG.exists():
    os.environ.setdefault("FARM_CONFIG", str(LOCAL_CONFIG))

import unittest

from message_handlers import handle_message
from state_store import FarmState


class IrrigatorVisualizationTests(unittest.TestCase):
    def test_live_irrigator_status_is_exposed(self):
        state = FarmState()

        handle_message(
            state,
            "camp/field_a/irrigator/status",
            {
                "status": "online",
                "operation": "irrigating",
                "active_request_id": "abc123",
                "last_amount": 7.0,
            },
        )

        snapshot = state.snapshot()
        irrigator = snapshot["camps"]["field_a"]["system"]["actuators"]["irrigator"]

        self.assertEqual(irrigator["status"], "ONLINE")
        self.assertEqual(irrigator["operation"], "irrigating")
        self.assertEqual(irrigator["active_request_id"], "abc123")

    def test_manager_system_status_exposes_pending_operation(self):
        state = FarmState()

        handle_message(
            state,
            "camp/field_a/system/status",
            {
                "overall_health": "HEALTHY",
                "sensors": {},
                "actuators": {
                    "irrigator": {
                        "status": "ONLINE",
                        "operation": "idle",
                    }
                },
                "automation": {
                    "irrigation": {
                        "pending": True,
                        "request_id": "req001",
                        "target_min_pct": 25.0,
                        "target_after_pct": 30.0,
                    },
                    "reoxygenation": {
                        "pending": False,
                        "request_id": None,
                        "threshold_pct": 30.0,
                    },
                },
            },
        )

        snapshot = state.snapshot()
        automation = snapshot["camps"]["field_a"]["system"]["automation"]
        self.assertTrue(automation["irrigation"]["pending"])
        self.assertEqual(automation["irrigation"]["request_id"], "req001")


if __name__ == "__main__":
    unittest.main()
