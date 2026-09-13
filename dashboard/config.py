"""Small configuration module.

All environment-dependent values live here so students do not have to search
through the application to change ports, broker credentials, or known fields.
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

CAMPS = ("campo_1", "campo_2", "campo_3")
MANAGER_HEARTBEAT_MAX_AGE_SECONDS = 15

# Topics published by the current camp manager / sensors.
TOPICS = (
    "camp/+/environment/telemetry",
    "camp/+/terrain/telemetry",
    "camp/+/plantation/status",
    "camp/+/system/status",
    "camp/+/camp_manager/#",
    "camp/manager/status",
    "camp/manager/#",
)
