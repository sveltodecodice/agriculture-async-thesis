"""Async MQTT transport for the dashboard using aiomqtt.

The dashboard follows the same MQTT/TLS contract used by Camp Manager and the
other farm services. MQTT runs in a dedicated asyncio loop on a background
thread while the HTTP/SSE server remains synchronous.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import ssl
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

import aiomqtt

from config import (
    MQTT_CA_CERT,
    MQTT_CLIENT_ID,
    MQTT_HOST,
    MQTT_KEEPALIVE,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_RECONNECT_SECONDS,
    MQTT_QOS,
    MQTT_TLS_MIN_VERSION,
    MQTT_USER,
    TOPICS,
)
from message_handlers import handle_message
from mqtt_contract import build_command
from state_store import STATE, utc_now

logger = logging.getLogger("dashboard.mqtt")


class MqttService:
    """Maintain one aiomqtt connection and expose thread-safe command publishing."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._runner_task: asyncio.Task | None = None
        self._client: aiomqtt.Client | None = None
        self._ready = threading.Event()
        self._stopping = threading.Event()

    @staticmethod
    def _tls_context() -> ssl.SSLContext:
        """Build a CA-verified TLS context for the MQTT broker."""
        versions = {
            "TLSv1.2": ssl.TLSVersion.TLSv1_2,
            "TLSv1.3": ssl.TLSVersion.TLSv1_3,
        }
        minimum = versions.get(MQTT_TLS_MIN_VERSION)
        if minimum is None:
            raise ValueError(f"Unsupported MQTT TLS minimum version: {MQTT_TLS_MIN_VERSION}")
        if not MQTT_CA_CERT or not os.path.exists(MQTT_CA_CERT):
            raise FileNotFoundError(f"MQTT CA certificate not found: {MQTT_CA_CERT}")

        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=MQTT_CA_CERT)
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        context.minimum_version = minimum
        return context

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stopping.clear()
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._thread_main,
            name="dashboard-mqtt",
            daemon=True,
        )
        self._thread.start()
        # Only wait for the event loop to exist, not for the broker to become
        # reachable. Reconnection continues in the background.
        self._ready.wait(timeout=5)

    def stop(self) -> None:
        self._stopping.set()
        loop = self._loop
        task = self._runner_task
        if loop and loop.is_running() and task:
            loop.call_soon_threadsafe(task.cancel)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._runner_task = loop.create_task(self._run_forever())
        self._ready.set()
        try:
            loop.run_until_complete(self._runner_task)
        except asyncio.CancelledError:
            pass
        finally:
            self._client = None
            STATE.set_mqtt(connected=False)
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
            self._loop = None
            self._runner_task = None

    async def _run_forever(self) -> None:
        while not self._stopping.is_set():
            try:
                logger.info(
                    "Connecting to MQTT broker %s:%s as %s",
                    MQTT_HOST,
                    MQTT_PORT,
                    MQTT_CLIENT_ID,
                )
                client = aiomqtt.Client(
                    MQTT_HOST,
                    MQTT_PORT,
                    username=MQTT_USER,
                    password=MQTT_PASSWORD,
                    tls_context=self._tls_context(),
                    identifier=MQTT_CLIENT_ID,
                    keepalive=MQTT_KEEPALIVE,
                    clean_session=False,
                )

                async with client:
                    self._client = client
                    for topic in TOPICS:
                        await client.subscribe(topic, qos=MQTT_QOS)
                        logger.info("Subscribed MQTT topic: %s", topic)

                    STATE.set_mqtt(connected=True, error=None)
                    logger.info("Dashboard MQTT connected")

                    async for message in client.messages:
                        await self._handle_message(message)

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Dashboard MQTT connection/listener error: %s", exc)
                STATE.set_mqtt(connected=False, error=f"{type(exc).__name__}: {exc}")
            finally:
                self._client = None

            if not self._stopping.is_set():
                await asyncio.sleep(MQTT_RECONNECT_SECONDS)

    async def _handle_message(self, message: aiomqtt.Message) -> None:
        topic = str(message.topic)
        try:
            raw = (
                message.payload.decode("utf-8")
                if isinstance(message.payload, bytes)
                else str(message.payload)
            )
            try:
                payload: Any = json.loads(raw)
            except json.JSONDecodeError:
                payload = raw

            handle_message(STATE, topic, payload)
            logger.debug("MQTT message received | topic=%s", topic)
        except Exception as exc:
            logger.exception("Failed to process MQTT message | topic=%s", topic)
            with STATE.lock:
                STATE.mqtt["last_error"] = f"{type(exc).__name__}: {exc}"
                STATE.touch()

    async def _publish(self, topic: str, payload: str) -> None:
        client = self._client
        with STATE.lock:
            connected = bool(STATE.mqtt.get("connected"))
        if client is None or not connected:
            raise ConnectionError("Il pannello non è connesso al server MQTT")
        await client.publish(topic, payload, qos=MQTT_QOS, retain=False)
        logger.info("MQTT command published | topic=%s | payload=%s", topic, payload)

    def send_command(self, camp_id: str, action: str, params: dict[str, Any]) -> dict[str, Any]:
        command = build_command(camp_id, action, params)
        record = {
            "camp_id": camp_id,
            "action": action,
            "params": params,
            "topic": command["topic"],
            "target_service": command["target_service"],
            "status": "error",
            "requested_at": utc_now(),
        }

        loop = self._loop
        if loop is None or not loop.is_running():
            record["error"] = "Il ciclo MQTT non è in esecuzione"
        else:
            future = asyncio.run_coroutine_threadsafe(
                self._publish(command["topic"], command["payload"]),
                loop,
            )
            try:
                future.result(timeout=5)
                record["status"] = "published"
            except FutureTimeoutError:
                future.cancel()
                record["error"] = "Tempo massimo superato durante la pubblicazione MQTT"
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
                with STATE.lock:
                    STATE.mqtt["last_error"] = record["error"]

        with STATE.lock:
            STATE.add_command(record)
            STATE.touch()

        if record["status"] != "published":
            raise ConnectionError(record.get("error", "Pubblicazione del comando MQTT non riuscita"))
        return record


MQTT = MqttService()
