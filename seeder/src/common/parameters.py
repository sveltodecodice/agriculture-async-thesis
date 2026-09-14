import os

# Credenziali MQTT
MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

# Topic Telemetria Inviata (Seeder -> Sistema)
TELEMETRY_ENV_TOPIC = "seeder/telemetry"

# Topic Comandi Ricevuti (Camp Manager -> Seeder)

FIELD_NAME = os.getenv("FIELD_NAME", "test")
