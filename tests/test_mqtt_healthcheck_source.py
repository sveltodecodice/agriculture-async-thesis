from pathlib import Path


def test_healthcheck_uses_full_mqtt_connection():
    source = Path("mqtt_tls_healthcheck.py").read_text(encoding="utf-8")

    assert "aiomqtt.Client" in source
    assert "async with client" in source
    assert "socket.create_connection" not in source
    assert "wrap_socket" not in source


def test_healthcheck_keeps_tls_verification_enabled():
    source = Path("mqtt_tls_healthcheck.py").read_text(encoding="utf-8")

    assert "ssl.CERT_REQUIRED" in source
    assert "check_hostname = True" in source
    assert "ssl.TLSVersion.TLSv1_2" in source
