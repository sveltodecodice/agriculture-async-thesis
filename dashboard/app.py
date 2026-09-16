"""Application entry point.

Start MQTT first, then expose the small HTTP/SSE server.
"""
from mqtt_service import MQTT
from http_server import run_http_server


def main() -> None:
    MQTT.start()
    try:
        run_http_server()
    finally:
        MQTT.stop()


if __name__ == "__main__":
    main()