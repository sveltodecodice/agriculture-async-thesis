"""Environment variables and operational parameters for MQTT connectivity."""

import os

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

FIELD_NAME = os.getenv("FIELD_NAME", "test")

TELEMETRY_ENV_TOPIC = "camp/{camp_id}/environment/telemetry"
CMD_ENV_TOPIC = f"camp/{FIELD_NAME}/environment/cmd/#"
