"""Environment variables and MQTT topic parameters for seeder service."""

import os

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

FIELD_NAME = os.getenv("FIELD_NAME", "test")

SEEDER_CMD_PLANT_TOPIC = f"camp/{FIELD_NAME}/seeder/cmd/plant"
PLANTATION_EVENT_SEEDED_TOPIC = f"camp/{FIELD_NAME}/plantation/event/seeded"
