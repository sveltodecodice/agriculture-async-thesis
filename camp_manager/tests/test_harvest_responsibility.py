import sys
from pathlib import Path

sys.path.append("src")


def test_camp_manager_does_not_persist_harvest_before_actuator_completion():
    source = Path("src/main.py").read_text(encoding="utf-8")
    assert "request_harvest" in source
    assert "save_harvest" not in source
    assert not Path("src/core/harvest_deposit.py").exists()
