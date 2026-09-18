from common.config_loader import env_value

MQTT_HOST = env_value("MQTT_BROKER_HOST", "mqtt.host", "mqtt-broker", str)
MQTT_PORT = env_value("MQTT_BROKER_PORT", "mqtt.port", 8883, int)
MQTT_USER = env_value("MQTT_BROKER_USER", "mqtt.username", "farm_admin", str)
MQTT_PASS = env_value("MQTT_BROKER_PASS", "mqtt.password", "secure_farm", str)
MQTT_CA_CERT = env_value("MQTT_CA_CERT", "mqtt.ca_cert", "/app/certs/ca.crt", str)
MQTT_RECONNECT_SECONDS = env_value("MQTT_RECONNECT_SECONDS", "mqtt.reconnect_seconds", 5, float)
MQTT_KEEPALIVE = env_value("MQTT_KEEPALIVE", "mqtt.keepalive", 60, int)
MQTT_TLS_MIN_VERSION = env_value("MQTT_TLS_MIN_VERSION", "mqtt.tls.minimum_version", "TLSv1.2", str)
MQTT_QOS = env_value("MQTT_QOS", "mqtt.qos", 2, int)

if MQTT_QOS != 2:
    raise ValueError("MQTT_QOS must be 2 to preserve maximum delivery guarantee")
FIELD_NAME = env_value("FIELD_NAME", "runtime.default_field", "test", str)

from common.config_loader import field_value

FIELD_INIT_TYPE = field_value(FIELD_NAME, "terrain.soil_type", "FIELD_INIT_TYPE", env_value("SOIL_LAYOUT_MODE", "simulation.soil_layout.mode", "Franco", str), str)
SOIL_LAYOUT_SEED = env_value("SOIL_LAYOUT_SEED", "simulation.soil_layout.seed", 2026, int)
FIELD_INIT_OXY = field_value(FIELD_NAME, "terrain.initial_oxygenation", "FIELD_INIT_OXY", 70.0, float)
FIELD_INIT_MOIST = field_value(FIELD_NAME, "terrain.initial_moisture", "FIELD_INIT_MOIST", 28.0, float)

ENV_TELEMETRY_TOPIC = f"camp/{FIELD_NAME}/environment/telemetry"
TERRAIN_EVENT_TOPIC = f"camp/{FIELD_NAME}/terrain/event/#"
TERRAIN_CMD_TOPIC = f"camp/{FIELD_NAME}/terrain/cmd/#"
TERRAIN_TELEMETRY_TOPIC = f"camp/{FIELD_NAME}/terrain/telemetry"
