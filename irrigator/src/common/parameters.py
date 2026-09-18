from common.config_loader import env_value

MQTT_HOST = env_value("MQTT_BROKER_HOST", "mqtt.host", "mqtt-broker", str)
MQTT_PORT = env_value("MQTT_BROKER_PORT", "mqtt.port", 8883, int)
MQTT_USER = env_value("MQTT_BROKER_USER", "mqtt.username", "farm_admin", str)
MQTT_PASSWORD = env_value("MQTT_BROKER_PASS", "mqtt.password", "", str)
MQTT_CA_CERT = env_value("MQTT_CA_CERT", "mqtt.ca_cert", "/app/certs/ca.crt", str)
MQTT_RECONNECT_SECONDS = env_value("MQTT_RECONNECT_SECONDS", "mqtt.reconnect_seconds", 5, float)
MQTT_KEEPALIVE = env_value("MQTT_KEEPALIVE", "mqtt.keepalive", 60, int)
MQTT_TLS_MIN_VERSION = env_value("MQTT_TLS_MIN_VERSION", "mqtt.tls.minimum_version", "TLSv1.2", str)
MQTT_QOS = env_value("MQTT_QOS", "mqtt.qos", 2, int)

if MQTT_QOS != 2:
    raise ValueError("MQTT_QOS must be 2 to preserve maximum delivery guarantee")
FIELD_NAME = env_value("FIELD_NAME", "runtime.default_field", "test", str)

IRRIGATE_CMD_TOPIC = f"camp/{FIELD_NAME}/irrigator/cmd/irrigate"
REOXYGENATE_CMD_TOPIC = f"camp/{FIELD_NAME}/irrigator/cmd/reoxygenate"
IRRIGATED_EVENT_TOPIC = f"camp/{FIELD_NAME}/terrain/event/irrigated"
REOXYGENATED_EVENT_TOPIC = f"camp/{FIELD_NAME}/terrain/event/reoxygenated"
IRRIGATOR_STATUS_TOPIC = f"camp/{FIELD_NAME}/irrigator/status"
IRRIGATOR_STATUS_INTERVAL_SECONDS = env_value("IRRIGATOR_STATUS_INTERVAL", "irrigator.status_interval_seconds", 5, float)
IRRIGATOR_ACTION_DELAY_SECONDS = env_value("IRRIGATOR_ACTION_DELAY", "irrigator.action_delay_seconds", 0.5, float)
IRRIGATOR_REOXYGENATION_TARGET = env_value("REOXYGENATION_TARGET", "irrigator.reoxygenation_target", 100.0, float)
