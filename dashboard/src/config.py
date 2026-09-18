"""Dashboard configuration. Environment variables override farm.yaml."""

from config_loader import env_list, env_value

HTTP_PORT = env_value("PORT", "dashboard.port", 8501, int)
MQTT_HOST = env_value("MQTT_BROKER_HOST", "mqtt.host", "mqtt-broker", str)
MQTT_PORT = env_value("MQTT_BROKER_PORT", "mqtt.port", 8883, int)
MQTT_USER = env_value("MQTT_BROKER_USER", "mqtt.username", "farm_admin", str)
MQTT_PASSWORD = env_value("MQTT_BROKER_PASS", "mqtt.password", "", str)
MQTT_CA_CERT = env_value("MQTT_CA_CERT", "mqtt.ca_cert", "/app/certs/ca.crt", str)
MQTT_KEEPALIVE = env_value("MQTT_KEEPALIVE", "mqtt.keepalive", 60, int)
MQTT_CLIENT_ID = env_value("MQTT_CLIENT_ID", "dashboard.mqtt_client_id", "smart-farm-dashboard", str)
MQTT_RECONNECT_SECONDS = env_value("MQTT_RECONNECT_SECONDS", "mqtt.reconnect_seconds", 5, float)
MQTT_TLS_MIN_VERSION = env_value("MQTT_TLS_MIN_VERSION", "mqtt.tls.minimum_version", "TLSv1.2", str)
MQTT_QOS = env_value("MQTT_QOS", "mqtt.qos", 2, int)

if MQTT_QOS != 2:
    raise ValueError("MQTT_QOS must be 2 to preserve maximum delivery guarantee")
CAMP_IDS = tuple(env_list("CAMP_IDS", "farm.fields", ["field_a", "field_b", "field_c"]))
MANAGER_HEARTBEAT_MAX_AGE_SECONDS = env_value("MANAGER_HEARTBEAT_MAX_AGE_SECONDS", "health.manager_heartbeat_max_age_seconds", 15, float)
SERVICE_HEARTBEAT_MAX_AGE_SECONDS = env_value("SERVICE_HEARTBEAT_MAX_AGE_SECONDS", "health.offline_after_seconds", 30, float)
DASHBOARD_POLL_INTERVAL_SECONDS = env_value("DASHBOARD_POLL_INTERVAL_SECONDS", "dashboard.polling_interval_seconds", 2, float)

TOPICS = (
    "camp/+/environment/telemetry",
    "camp/+/terrain/telemetry",
    "camp/+/plantation/status",
    "camp/+/system/status",
    "camp/+/irrigator/status",
    "camp/+/heartbeat/+",
    "camp/manager/status",
    "camp/notifications",
    "camp/activity_logs",
)
