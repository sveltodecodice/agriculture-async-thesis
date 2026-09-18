from common.config_loader import env_value

MQTT_HOST = env_value("MQTT_BROKER_HOST", "mqtt.host", "mqtt-broker", str)
MQTT_PORT = env_value("MQTT_BROKER_PORT", "mqtt.port", 8883, int)
MQTT_USER = env_value("MQTT_BROKER_USER", "mqtt.username", "farm_admin", str)
MQTT_PASS = env_value("MQTT_BROKER_PASS", "mqtt.password", "secure_farm", str)
MQTT_CA_CERT = env_value("MQTT_CA_CERT", "mqtt.ca_cert", "/app/certs/ca.crt", str)
MQTT_RECONNECT_SECONDS = env_value("MQTT_RECONNECT_SECONDS", "mqtt.reconnect_seconds", 5, float)
FIELD_NAME = env_value("FIELD_NAME", "runtime.default_field", "test", str)

TELEMETRY_ENV_TOPIC = "camp/{camp_id}/environment/telemetry"
CMD_ENV_TOPIC = f"camp/{FIELD_NAME}/environment/cmd/#"
ENV_PUBLISH_INTERVAL_SECONDS = env_value("ENV_PUBLISH_INTERVAL_SECONDS", "simulation.environment_publish_interval_seconds", 10, float)
SIMULATION_START_DATE = env_value("SIMULATION_START_DATE", "simulation.start_date", "01/01/2026", str)
