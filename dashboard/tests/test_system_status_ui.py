from pathlib import Path


def test_sidebar_contains_only_requested_sections():
    index = Path("templates/index.html").read_text(encoding="utf-8")

    assert "Panoramica" in index
    assert "Stato Sistema" in index
    assert "Notifiche Sistema" in index
    assert "Centro di controllo" not in index
    assert 'id="fieldNav"' not in index
    assert 'data-route="activity"' not in index
    assert 'data-route="diagnostics"' not in index


def test_previous_palette_is_restored():
    css = Path("static/styles.css").read_text(encoding="utf-8").lower()

    for color in ("#f4f2eb", "#fffdf8", "#173c2d", "#2f674e", "#ad5847"):
        assert color in css

    for removed in ("#f2af29", "#823200", "#e0e0ce", "#337357", "#1a1d1a"):
        assert removed not in css


def test_frontend_uses_requested_view_specific_endpoints():
    app = Path("static/app.js").read_text(encoding="utf-8")

    assert "/api/overview" in app
    assert "/api/notifications" in app
    assert "/api/system-status" in app
    assert "/api/activity" not in app
    assert "/api/state" not in app


def test_current_simulation_day_is_shown_only_in_weather_section():
    app = Path("static/app.js").read_text(encoding="utf-8")

    assert app.count("Giorno simulato") == 1
    assert app.count("farmDate()") == 2  # function definition + Meteo corrente use
    assert "e.date" not in app


def test_system_status_uses_italian_labels_and_all_field_services():
    app = Path("static/app.js").read_text(encoding="utf-8")

    for label in (
        "Pannello di controllo",
        "Gestore centrale",
        "Sensore ambientale",
        "Sensore terreno",
        "Sensore piantagione",
        "Irrigatore",
        "Seminatrice",
        "Raccoglitore",
    ):
        assert label in app

    assert "Stato non monitorato" not in app
