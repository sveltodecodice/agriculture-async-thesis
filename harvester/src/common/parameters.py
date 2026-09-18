from common.config_loader import env_value

MQTT_HOST = env_value("MQTT_BROKER_HOST", "mqtt.host", "mqtt-broker", str)
MQTT_PORT = env_value("MQTT_BROKER_PORT", "mqtt.port", 8883, int)
MQTT_USER = env_value("MQTT_BROKER_USER", "mqtt.username", "farm_admin", str)
MQTT_PASS = env_value("MQTT_BROKER_PASS", "mqtt.password", "secure_farm", str)
MQTT_CA_CERT = env_value("MQTT_CA_CERT", "mqtt.ca_cert", "/app/certs/ca.crt", str)
MQTT_RECONNECT_SECONDS = env_value("MQTT_RECONNECT_SECONDS", "mqtt.reconnect_seconds", 5, float)
FIELD_NAME = env_value("FIELD_NAME", "runtime.default_field", "test", str)

HARVEST_CMD_TOPIC = f"camp/{FIELD_NAME}/harvester/cmd/harvest"
HARVEST_DEPOSIT_TOPIC = "camp/harvest_deposit"
HARVEST_EVENT_TOPIC = f"camp/{FIELD_NAME}/plantation/event/harvested"
