"""Dashboard configuration.

The dashboard follows the same field identifiers as the distributed farm.
Set CAMP_IDS to the same comma-separated list used by Camp Manager.
"""
from __future__ import annotations

import os

HTTP_PORT = int(os.getenv("PORT", "8501"))

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "8883"))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASSWORD = os.getenv("MQTT_BROKER_PASS", "secure_farm")
MQTT_CA_CERT = os.getenv("MQTT_CA_CERT", "/app/certs/ca.crt")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))


def configured_camps() -> tuple[str, ...]:
    raw = os.getenv("CAMP_IDS", "field_a,field_b,field_c")
    camps = tuple(camp.strip() for camp in raw.split(",") if camp.strip())
    if not camps:
        raise ValueError("CAMP_IDS must contain at least one field id")
    return camps


CAMPS = configured_camps()
MANAGER_HEARTBEAT_MAX_AGE_SECONDS = 15

# The dashboard consumes observations and manager health only. Actuator events are
# intentionally not used as UI truth: their effects are confirmed through sensor
# telemetry/status, matching the system feedback-loop architecture.
TOPICS = (
    "camp/+/environment/telemetry",
    "camp/+/terrain/telemetry",
    "camp/+/plantation/status",
    "camp/+/system/status",
    "camp/manager/status",
)
