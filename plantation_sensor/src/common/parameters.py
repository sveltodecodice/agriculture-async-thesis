"""Environment variables and operational parameters for plantation sensor MQTT communication."""

import os

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

FIELD_NAME = os.getenv("FIELD_NAME", "test")

TERRAIN_TELEMETRY_TOPIC = f"camp/{FIELD_NAME}/terrain/telemetry"
ENV_TELEMETRY_TOPIC = f"camp/{FIELD_NAME}/environment/telemetry"
PLANTATION_EVENT_TOPIC = f"camp/{FIELD_NAME}/plantation/event/#"
