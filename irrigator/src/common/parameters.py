"""Environment variables and operational parameters for irrigator MQTT communication."""

import os

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

FIELD_NAME = os.getenv("FIELD_NAME", "test")

IRRIGATE_CMD_TOPIC = f"camp/{FIELD_NAME}/irrigator/cmd/irrigate"
REOXYGENATE_CMD_TOPIC = f"camp/{FIELD_NAME}/irrigator/cmd/reoxygenate"

IRRIGATED_EVENT_TOPIC = f"camp/{FIELD_NAME}/terrain/event/irrigated"
REOXYGENATED_EVENT_TOPIC = f"camp/{FIELD_NAME}/terrain/event/reoxygenated"
