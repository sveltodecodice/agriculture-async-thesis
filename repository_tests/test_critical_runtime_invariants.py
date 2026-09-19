from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_service_heartbeats_include_source_timestamp():
    services = [
        "ambient_sensor",
        "terrain_sensor",
        "plantation_sensor",
        "seeder",
        "harvester",
    ]

    for service in services:
        source = (ROOT / service / "src/main.py").read_text(encoding="utf-8")
        assert '"ts": time()' in source, service


def test_default_mqtt_password_is_not_committed():
    farm_yaml = (ROOT / "config/farm.yaml").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "password: secure_farm" not in farm_yaml
    assert "MQTT_BROKER_PASS:-secure_farm" not in compose
    assert "MQTT_BROKER_PASS:?" in compose

    for path in ROOT.rglob("*.py"):
        if any(part in {"tests", ".pytest_cache", "__pycache__"} for part in path.parts):
            continue
        assert '"secure_farm"' not in path.read_text(encoding="utf-8"), path
