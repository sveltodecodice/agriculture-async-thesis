import json
import sys
from pathlib import Path

sys.path.append("src")

from core import harvester_deposit


def test_save_harvest_appends_to_shared_history(tmp_path, monkeypatch):
    deposit = tmp_path / "harvest_deposit.json"
    monkeypatch.setattr(harvester_deposit, "DATA_OUTPUT_PATH", str(deposit))
    monkeypatch.setattr(harvester_deposit, "LOCK_PATH", f"{deposit}.lock")

    first = harvester_deposit.save_harvest("tomato", "01/01/2026")
    second = harvester_deposit.save_harvest("wheat", "02/01/2026")

    assert len(first) == 1
    assert [item["seed"] for item in second] == ["tomato", "wheat"]
    assert json.loads(deposit.read_text(encoding="utf-8")) == second


def test_harvest_persistence_uses_exclusive_file_lock():
    source = Path("src/core/harvester_deposit.py").read_text(encoding="utf-8")

    assert "fcntl.LOCK_EX" in source
    assert "os.replace" in source
