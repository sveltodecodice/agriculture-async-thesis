import sys
from pathlib import Path

sys.path.append("src")

from common.parameters import MQTT_KEEPALIVE, MQTT_QOS


def test_mqtt_uses_maximum_qos_and_keepalive():
    assert MQTT_QOS == 2
    assert MQTT_KEEPALIVE > 0


def test_no_insecure_tls_bypass_in_runtime_code():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src").rglob("*.py")
    )
    assert "ssl.CERT_NONE" not in source
    assert "check_hostname = False" not in source
    assert "qos=1" not in source


def test_tls_context_verifies_server_certificate(monkeypatch):
    import ssl
    from utils import mqtt_utils

    system_ca = ssl.get_default_verify_paths().cafile
    if not system_ca:
        return

    monkeypatch.setattr(mqtt_utils, "MQTT_CA_CERT", system_ca)
    monkeypatch.setattr(mqtt_utils, "MQTT_TLS_MIN_VERSION", "TLSv1.2")
    context = mqtt_utils.build_tls_context()

    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
