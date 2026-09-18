import sys
from pathlib import Path

sys.path.append("src")

from common.parameters import FIELD_NAME, HEARTBEAT_INTERVAL_SECONDS, HEARTBEAT_TOPIC


def test_heartbeat_configuration_is_available():
    assert HEARTBEAT_INTERVAL_SECONDS > 0
    assert HEARTBEAT_TOPIC == f"camp/{FIELD_NAME}/heartbeat/plantation_sensor"


def test_service_runs_periodic_heartbeat_loop():
    source = Path("src/main.py").read_text(encoding="utf-8")
    assert "async def heartbeat_loop" in source
    assert "retain=True" in source
    assert "HEARTBEAT_INTERVAL_SECONDS" in source
