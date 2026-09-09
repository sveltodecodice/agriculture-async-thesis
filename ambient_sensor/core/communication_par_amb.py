import os

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

AMQP_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
AMQP_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
AMQP_USER = os.getenv("RABBITMQ_USER", "farm_admin")
AMQP_PASS = os.getenv("RABBITMQ_PASS", "secure_farm")

AMQP_URL = f"amqp://{AMQP_USER}:{AMQP_PASS}@{AMQP_HOST}:{AMQP_PORT}/"
TELEMETRY_TOPIC = "environment/telemetry"