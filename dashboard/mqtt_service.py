"""MQTT transport only: connect, subscribe, decode, publish."""
from __future__ import annotations

import json
import os
import ssl
from typing import Any

import paho.mqtt.client as mqtt

from config import MQTT_CA_CERT, MQTT_HOST, MQTT_KEEPALIVE, MQTT_PASSWORD, MQTT_PORT, MQTT_USER, TOPICS
from message_handlers import handle_message
from mqtt_contract import build_command
from state_store import STATE, utc_now


class MqttService:
    def __init__(self) -> None:
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

        context = ssl.create_default_context(cafile=MQTT_CA_CERT if os.path.exists(MQTT_CA_CERT) else None)
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        self.client.tls_set_context(context)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def start(self) -> None:
        self.client.connect_async(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        connected = str(reason_code).lower() in {"success", "0"}
        try:
            connected = connected or int(reason_code) == 0
        except Exception:
            pass
        STATE.set_mqtt(connected=connected, error=None if connected else str(reason_code))
        if connected:
            for topic in TOPICS:
                client.subscribe(topic, qos=1)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None) -> None:
        STATE.set_mqtt(connected=False, error=str(reason_code))

    def _on_message(self, client, userdata, message) -> None:
        try:
            text = message.payload.decode("utf-8")
            try:
                payload: Any = json.loads(text)
            except json.JSONDecodeError:
                payload = text
            handle_message(STATE, str(message.topic), payload)
        except Exception as exc:
            with STATE.lock:
                STATE.mqtt["last_error"] = str(exc)
                STATE.touch()

    def send_command(self, camp_id: str, action: str, params: dict[str, Any]) -> dict[str, Any]:
        command = build_command(camp_id, action, params)
        info = self.client.publish(command.topic, command.payload, qos=1, retain=False)
        ok = info.rc == mqtt.MQTT_ERR_SUCCESS
        record = {
            "camp_id": camp_id,
            "action": action,
            "params": params,
            "topic": command.topic,
            "target_service": command.target_service,
            "status": "published" if ok else "error",
            "requested_at": utc_now(),
        }
        with STATE.lock:
            STATE.add_command(record)
            STATE.touch()
        return record


MQTT = MqttService()
