import os

# Credenziali MQTT
MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 8883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")


FIELD_NAME = os.getenv("FIELD_NAME", "test")
HARVEST_DEPOSIT_TOPIC = "camp/harvest_deposit"
