import os

# MQTT Credentials
MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

# Telemetry Topics
TELEMETRY_IN_TOPIC = "environment/telemetry"
TELEMETRY_OUT_TOPIC = "camp/terrain_telemetry"

# Command Topics
CMD_TERRAIN_TOPIC = "terrain/cmd/#"

# Field specification
FIELD_NAME = os.getenv("FIELD_NAME", "test")
FIELD_INIT_TYPE = os.getenv("FIELD_INIT_TYPE", "Franco")
FIELD_INIT_OXY = float(os.getenv("FIELD_INIT_OXY", 70.0))
FIELD_INIT_MOIST = float(os.getenv("FIELD_INIT_MOIST", 28.0))
