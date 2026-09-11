import os

# Credenziali MQTT
MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

# Topic Telemetria (Sensori -> Manager)
TELEMETRY_ENV_TOPIC = "environment/telemetry"
TELEMETRY_TERRAIN_TOPIC = "camp/terrain_telemetry"
PLANTATION_STATUS_TOPIC = "plantation/status"

# Topic Dashboard & Notifiche (Manager -> Node-RED)
NOTIFICATIONS_TOPIC = "camp/notifications"
ACTIVITY_LOGS_TOPIC = "camp/activity_logs"
HARVEST_DEPOSIT_TOPIC = "camp/harvest_deposit"
TOP_SEEDS_TOPIC = "camp/top_seeds"

# Topic Comandi (Manager -> Sensori)
CMD_ENV_TOPIC = "environment/cmd/#"
CMD_TERRAIN_TOPIC = "terrain/cmd/#"
CMD_PLANTATION_TOPIC = "plantation/cmd/#"