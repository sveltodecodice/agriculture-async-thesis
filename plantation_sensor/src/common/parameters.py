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

TERRAIN_TELEMETRY_TOPIC = f"camp/{FIELD_NAME}/terrain/telemetry"
ENV_TELEMETRY_TOPIC = f"camp/{FIELD_NAME}/environment/telemetry"
PLANTATION_EVENT_TOPIC = f"camp/{FIELD_NAME}/plantation/event/#"
PLANTATION_PUBLISH_INTERVAL_SECONDS = env_value("PLANTATION_PUBLISH_INTERVAL_SECONDS", "simulation.plantation_publish_interval_seconds", 3, float)

HEARTBEAT_INTERVAL_SECONDS = env_value(
    "HEARTBEAT_INTERVAL_SECONDS",
    "health.publish_interval_seconds",
    5,
    float,
)
HEARTBEAT_TOPIC = f"camp/{FIELD_NAME}/heartbeat/plantation_sensor"
