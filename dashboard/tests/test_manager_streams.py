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


class ManagerStreamTests(unittest.TestCase):
    def test_notification_is_recorded(self):
        state = FarmState()
        handle_message(state, "camp/notifications", "[FIELD_A] Test manager notification")
        snap = state.snapshot()
        self.assertEqual(snap["notifications"][-1]["camp_id"], "field_a")
        self.assertIn("Test manager", snap["notifications"][-1]["message"])

    def test_activity_filters_old_topology(self):
        state = FarmState()
        handle_message(state, "camp/activity_logs", [
            {"date": "01/01/2026", "event": "AUTO_PLANT", "details": "[campo_1] old"},
            {"date": "02/01/2026", "event": "AUTO_IRRIGATE", "details": "[field_a] current"},
        ])
        snap = state.snapshot()
        self.assertEqual(len(snap["activity"]), 1)
        self.assertEqual(snap["activity"][0]["camp_id"], "field_a")


if __name__ == "__main__":
    unittest.main()
