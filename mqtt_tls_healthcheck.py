"""Docker healthcheck: verify MQTT authentication over validated TLS.

This performs a real MQTT CONNECT/DISCONNECT instead of opening and
abruptly closing a raw TLS socket. That keeps Mosquitto logs clean while
still validating DNS, TLS certificate/hostname, credentials and MQTT.
"""

import asyncio
import os
import socket
import ssl
from pathlib import Path

import aiomqtt
import yaml


def load_config() -> dict:
    path = Path(os.getenv("FARM_CONFIG", "/app/config/farm.yaml"))

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    return data if isinstance(data, dict) else {}


def nested(config: dict, path: str, default=None):
    value = config

    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]

    return value


def build_tls_context(config: dict) -> ssl.SSLContext:
    cafile = (
        os.getenv("MQTT_CA_CERT")
        or nested(config, "mqtt.ca_cert", "/app/certs/ca.crt")
    )

    minimum_name = (
        os.getenv("MQTT_TLS_MIN_VERSION")
        or nested(config, "mqtt.tls.minimum_version", "TLSv1.2")
    )

    versions = {
        "TLSv1.2": ssl.TLSVersion.TLSv1_2,
        "TLSv1.3": ssl.TLSVersion.TLSv1_3,
    }

    minimum = versions.get(str(minimum_name))
    if minimum is None:
        raise ValueError(f"Unsupported TLS version: {minimum_name}")

    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH,
        cafile=str(cafile),
    )
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.minimum_version = minimum

    return context


async def check_mqtt() -> None:
    config = load_config()

    host = (
        os.getenv("MQTT_BROKER_HOST")
        or nested(config, "mqtt.host", "mqtt-broker")
    )
    port = int(
        os.getenv("MQTT_BROKER_PORT")
        or nested(config, "mqtt.port", 8883)
    )
    username = (
        os.getenv("MQTT_BROKER_USER")
        or nested(config, "mqtt.username", "farm_admin")
    )
    password = (
        os.getenv("MQTT_BROKER_PASS")
        or nested(config, "mqtt.password", "")
    )

    # Unique for each container, short enough for MQTT 3.1.1 brokers.
    client_id = f"hc-{socket.gethostname()}"[:23]

    client = aiomqtt.Client(
        str(host),
        port,
        username=str(username),
        password=str(password),
        tls_context=build_tls_context(config),
        identifier=client_id,
        keepalive=10,
        clean_session=True,
    )

    # Entering the context performs a real MQTT CONNECT.
    # Exiting it performs a normal MQTT DISCONNECT.
    async with asyncio.timeout(6):
        async with client:
            pass


def main() -> int:
    try:
        asyncio.run(check_mqtt())
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
