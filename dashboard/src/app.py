"""Smart Farm dashboard entry point."""
import logging

from http_server import run_http_server
from mqtt_service import MQTT


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    MQTT.start()
    try:
        run_http_server()
    finally:
        MQTT.stop()


if __name__ == "__main__":
    main()
