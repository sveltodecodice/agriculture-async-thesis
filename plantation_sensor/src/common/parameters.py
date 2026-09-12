import os

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

TELEMETRY_ENV_TOPIC = "environment/telemetry"
TELEMETRY_TERRAIN_TOPIC = "camp/terrain_telemetry"
PLANTATION_STATUS_TOPIC = "plantation/status"

CMD_PLANTATION_TOPIC = "plantation/cmd/#"
