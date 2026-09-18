from common.config_loader import env_list, env_value

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
MQTT_CLIENT_ID = env_value("MQTT_CLIENT_ID", "camp_manager.mqtt_client_id", "camp-manager-app", str)
CAMP_IDS = env_list("CAMP_IDS", "farm.fields", ["field_a", "field_b", "field_c"])

SENSOR_OFFLINE_SECONDS = env_value("SENSOR_OFFLINE_SECONDS", "health.offline_after_seconds", 30.0, float)
HEALTH_PUBLISH_INTERVAL_SECONDS = env_value("HEALTH_PUBLISH_INTERVAL_SECONDS", "health.publish_interval_seconds", 5, float)
MANAGER_HEARTBEAT_INTERVAL_SECONDS = env_value("MANAGER_HEARTBEAT_INTERVAL_SECONDS", "health.manager_heartbeat_interval_seconds", 5, float)
AUTO_SEED_EMPTY_DAYS = env_value("AUTO_SEED_EMPTY_DAYS", "automation.planting.empty_days_before_auto_seed", 3, int)
AUTO_SEED_CHECK_INTERVAL_SECONDS = env_value("AUTO_SEED_CHECK_INTERVAL_SECONDS", "automation.planting.check_interval_seconds", 4, float)
EMPTY_FIELD_MIN_MOISTURE = env_value("EMPTY_FIELD_MIN_MOISTURE", "automation.irrigation.empty_field_min_moisture", 15.0, float)
IRRIGATION_TARGET_MARGIN = env_value("IRRIGATION_TARGET_MARGIN", "automation.irrigation.target_margin", 5.0, float)
MIN_IRRIGATION_AMOUNT = env_value("MIN_IRRIGATION_AMOUNT", "automation.irrigation.minimum_amount_pct", 2.0, float)
OXYGENATION_THRESHOLD = env_value("OXYGENATION_THRESHOLD", "automation.oxygenation.minimum_percentage", 30.0, float)

NOTIFICATIONS_TOPIC = "camp/notifications"
ACTIVITY_LOGS_TOPIC = "camp/activity_logs"
TOP_SEEDS_TOPIC = "camp/top_seeds"
CAMP_MANAGER_STATUS_TOPIC = "camp/manager/status"
