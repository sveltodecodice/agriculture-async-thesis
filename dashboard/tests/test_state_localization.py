import sys
from pathlib import Path

sys.path.append("src")


def test_all_backend_growth_stages_have_italian_mapping():
    source = Path("static/app.js").read_text(encoding="utf-8")
    for state in (
        "EMPTY", "PLANTED", "GERMINATION", "VEGETATIVE",
        "MATURING", "READY_FOR_HARVEST", "UNKNOWN",
    ):
        assert f"{state}:" in source


def test_service_and_health_states_have_italian_mapping():
    source = Path("static/app.js").read_text(encoding="utf-8")
    for state in (
        "ONLINE", "OFFLINE", "HEALTHY", "DEGRADED",
        "FIELD IS EMPTY", "TOO_DRY", "TOO_WET",
        "TOO_COLD", "TOO_HOT", "UNFAVORABLE_SEASON", "UNKNOWN",
    ):
        assert state in source


def test_machine_state_fallbacks_do_not_echo_unknown_english_values():
    source = Path("static/app.js").read_text(encoding="utf-8")
    assert "|| (v || '—')" not in source
    assert "GERMINATION:'Germinazione'" in source
