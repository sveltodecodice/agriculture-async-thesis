from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from copy import deepcopy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import ssl
import threading
from typing import Any
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from mqtt_contract import (
    ACTIONS,
    CAMPS,
    SCHEMA_VERSION,
    ack_envelope,
    command_envelope,
    command_topic,
    state_topic,
    to_legacy_command,
    utc_now,
)
from seeds import CROPS_INFO, CROP_KEY_TO_NAME

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = BASE_DIR / "templates" / "index.html"

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "8883"))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")
MQTT_CA_CERT = os.getenv("MQTT_CA_CERT", "/app/certs/ca.crt")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
PORT = int(os.getenv("PORT", "8501"))

SOIL_TYPES = ["Franco", "Argilloso", "Sabbioso", "Franco-Sabbioso", "Franco-Argilloso"]
EMPTY_PLANT_NAMES = {"", "none", "unknown", "vacant", "empty", "field is empty", "nessuna", "clear"}
STATUS_BLACKLIST = {
    "too_wet", "too_dry", "healthy", "ok", "clear", "trigger", "sospesa", "attiva",
    "none", "unknown", "vacant", "field is empty", "nessuna",
}


def _empty_camp() -> dict[str, Any]:
    return {
        "environment": {
            "date": None,
            "short_date": None,
            "season": None,
            "weather": None,
            "temperature": None,
            "humidity_air": None,
            "rain_mm": None,
            "wind_kmh": None,
            "radiation_wm2": None,
        },
        "terrain": {
            "soil_moisture": None,
            "oxygenation": None,
            "soil_type": None,
            "water_dispensed_mm": None,
            "moisture_loss_today": None,
            "irrigation_active": None,
        },
        "plantation": {
            "crop": "Nessuna",
            "crop_key": None,
            "occupied": False,
            "camp_availability": None,
            "time_left": None,
            "growth_percentage": 0.0,
            "growth_stage": "EMPTY",
            "health": "FIELD IS EMPTY",
            "min_moisture": None,
            "max_moisture": None,
            "age_days": None,
            "harvest_days": None,
            "planted_date": None,
            "last_status_at": None,
        },
        "manager": {},
        "system": {
            "mqtt_connected": None,
            "overall_health": "UNKNOWN",
            "sensors": {
                "environment": {"status": "UNKNOWN", "last_seen_seconds_ago": None, "latency_ms": None},
                "terrain": {"status": "UNKNOWN", "last_seen_seconds_ago": None, "latency_ms": None},
                "plantation": {"status": "UNKNOWN", "last_seen_seconds_ago": None, "latency_ms": None},
            },
            "updated_at": None,
            "received_at": None,
        },
        "last_seen": None,
    }


class FarmState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.revision = 0
        self.camps = {camp_id: _empty_camp() for camp_id in CAMPS}
        self.activity: deque[dict[str, Any]] = deque(maxlen=250)
        self.harvests: deque[dict[str, Any]] = deque(maxlen=100)
        self.commands: deque[dict[str, Any]] = deque(maxlen=100)
        self._activity_seen: set[str] = set()
        self._harvest_seen: set[str] = set()
        self.mqtt = {
            "connected": False,
            "last_message_at": None,
            "last_topic": None,
            "last_error": None,
        }
        self.camp_manager = {
            "connected": False,
            "status": "unknown",
            "service": "camp_manager",
            "last_heartbeat": None,
            "camps": [],
        }

    def touch(self) -> None:
        self.revision += 1
        self.changed.notify_all()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            manager = deepcopy(self.camp_manager)
            heartbeat = manager.get("last_heartbeat")
            manager["connected"] = False
            if heartbeat:
                try:
                    stamp = datetime.fromisoformat(str(heartbeat).replace("Z", "+00:00"))
                    if stamp.tzinfo is None:
                        stamp = stamp.replace(tzinfo=timezone.utc)
                    manager["connected"] = (datetime.now(timezone.utc) - stamp).total_seconds() <= 15
                except (TypeError, ValueError):
                    manager["connected"] = False
            return {
                "schema_version": SCHEMA_VERSION,
                "revision": self.revision,
                "generated_at": utc_now(),
                "mqtt": deepcopy(self.mqtt),
                "camp_manager": manager,
                "camps": deepcopy(self.camps),
                "activity": list(self.activity)[-80:],
                "harvests": list(self.harvests)[-40:],
                "commands": list(self.commands)[-30:],
            }

    def add_activity_record(self, record: dict[str, Any], *, dedupe_key: str | None = None) -> None:
        key = dedupe_key or json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)
        if key in self._activity_seen:
            return
        self._activity_seen.add(key)
        self.activity.append(record)
        if len(self._activity_seen) > 1000:
            self._activity_seen = {
                json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
                for item in list(self.activity)
            }

    def add_harvest_record(self, record: dict[str, Any], *, dedupe_key: str | None = None) -> None:
        key = dedupe_key or json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)
        if key in self._harvest_seen:
            return
        self._harvest_seen.add(key)
        self.harvests.append(record)
        if len(self._harvest_seen) > 500:
            self._harvest_seen = {
                json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
                for item in list(self.harvests)
            }


STATE = FarmState()

ALIASES = {
    "temperature": "temperature", "temp": "temperature", "temp_aria": "temperature",
    "humidity_air": "humidity_air", "humidity": "humidity_air", "air_humidity": "humidity_air",
    "rain_mm": "rain_mm", "rain": "rain_mm", "pioggia": "rain_mm",
    "wind_kmh": "wind_kmh", "wind": "wind_kmh", "vento": "wind_kmh",
    "radiation_wm2": "radiation_wm2", "radiation": "radiation_wm2", "radiazione": "radiation_wm2",
    "soil_moisture": "soil_moisture", "moisture": "soil_moisture", "umidita_suolo": "soil_moisture",
    "oxygenation": "oxygenation", "ossigenazione": "oxygenation", "oxygen": "oxygenation",
    "water_dispensed_mm": "water_dispensed_mm", "water_applied_mm": "water_dispensed_mm", "erogata": "water_dispensed_mm",
    "soil_type": "soil_type", "terrain_type": "soil_type",
}


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    norm: dict[str, Any] = {}
    for key, value in payload.items():
        norm[ALIASES.get(str(key).lower(), key)] = value
    if all(k in payload for k in ("day", "month", "year")):
        try:
            norm["date"] = f"{int(payload['day']):02d}/{int(payload['month']):02d}/{int(payload['year'])}"
            norm["short_date"] = f"{int(payload['day']):02d}/{int(payload['month']):02d}"
        except (TypeError, ValueError):
            pass
    return norm


def normalize_moisture(value: Any) -> Any:
    """Canonical dashboard moisture is always a fraction (0.25 == 25%)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    return number / 100.0 if abs(number) > 1.0 else number


def normalize_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "on", "occupied", "available"}:
        return True
    if text in {"false", "0", "no", "off", "empty", "vacant"}:
        return False
    return None


def extract_camp_id(topic: str, payload: dict[str, Any] | None = None) -> str | None:
    payload = payload or {}
    parts = topic.split("/")
    if len(parts) > 1 and parts[0] == "camp" and parts[1] in CAMPS:
        return parts[1]
    raw = str(payload.get("camp_id") or payload.get("Campo") or "").strip().lower().replace(" ", "_")
    if raw in CAMPS:
        return raw
    lowered = topic.lower()
    return next((camp for camp in CAMPS if camp in lowered), None)


def extract_camp_from_text(text: Any) -> str | None:
    lowered = str(text or "").lower()
    return next((camp for camp in CAMPS if camp in lowered), None)


def display_crop_name(raw_crop: Any) -> tuple[str, str | None]:
    raw = str(raw_crop or "").strip()
    key = raw.lower().replace("-", "_")
    if key in EMPTY_PLANT_NAMES:
        return "Nessuna", None
    mapped = CROP_KEY_TO_NAME.get(key) or CROP_KEY_TO_NAME.get(key.replace("_", " "))
    return (mapped or raw, key or None)


def canonical_record(camp_id: str, domain: str, data: dict[str, Any], source_topic: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "camp_id": camp_id,
        "domain": domain,
        "observed_at": utc_now(),
        "source_topic": source_topic,
        "data": data,
    }


def publish_canonical_state(camp_id: str, domain: str, data: dict[str, Any], source_topic: str) -> None:
    record = canonical_record(camp_id, domain, data, source_topic)
    MQTT.publish(state_topic(camp_id, domain), json.dumps(record, ensure_ascii=False), qos=1, retain=True)


def add_activity(topic: str, payload: dict[str, Any], camp_id: str | None = None, kind: str = "event") -> None:
    STATE.add_activity_record({
        "received_at": utc_now(),
        "camp_id": camp_id,
        "kind": kind,
        "topic": topic,
        "event": payload.get("event") if isinstance(payload, dict) else None,
        "event_date": payload.get("date") if isinstance(payload, dict) else None,
        "details": payload.get("details") if isinstance(payload, dict) else None,
        "payload": payload,
    })


def ingest_activity_feed(topic: str, payload: Any) -> None:
    records = payload if isinstance(payload, list) else [payload]
    for entry in records:
        if not isinstance(entry, dict):
            continue
        camp_id = extract_camp_id(topic, entry) or extract_camp_from_text(entry.get("details"))
        key = f"{entry.get('date')}|{entry.get('event')}|{entry.get('details')}"
        STATE.add_activity_record({
            "received_at": utc_now(),
            "camp_id": camp_id,
            "kind": "activity",
            "topic": topic,
            "event": entry.get("event") or "EVENT",
            "event_date": entry.get("date"),
            "details": entry.get("details"),
            "payload": entry,
        }, dedupe_key=key)


def ingest_harvest_feed(topic: str, payload: Any) -> None:
    records = payload if isinstance(payload, list) else [payload]
    for entry in records:
        if not isinstance(entry, dict):
            continue
        camp_id = extract_camp_id(topic, entry) or extract_camp_from_text(entry)
        seed = entry.get("seed") or entry.get("Coltivazione") or entry.get("crop")
        harvested_on = entry.get("harvested_on") or entry.get("Data Raccolta") or entry.get("date")
        key = f"{camp_id}|{seed}|{harvested_on}|{json.dumps(entry, sort_keys=True, ensure_ascii=False, default=str)}"
        STATE.add_harvest_record({
            "received_at": utc_now(),
            "camp_id": camp_id,
            "seed": seed,
            "harvested_on": harvested_on,
            "payload": entry,
        }, dedupe_key=key)


def update_plantation_from_status(camp_id: str, camp: dict[str, Any], norm: dict[str, Any], topic: str) -> None:
    plantation = camp["plantation"]
    detail = norm.get("status_detail") if isinstance(norm.get("status_detail"), dict) else {}
    has_new_shape = "status_detail" in norm or "camp_availability" in norm

    raw_crop = (
        detail.get("plant_name")
        or norm.get("crop")
        or norm.get("plant")
        or norm.get("seed_name")
        or norm.get("name")
        or norm.get("value")
    )
    crop_name, crop_key = display_crop_name(raw_crop)

    availability = normalize_bool(norm.get("camp_availability"))
    valid_crop = crop_name != "Nessuna"
    occupied = (availability is True and valid_crop) if has_new_shape else valid_crop

    if not occupied:
        plantation.update({
            "crop": "Nessuna",
            "crop_key": None,
            "occupied": False,
            "camp_availability": availability,
            "time_left": None,
            "growth_percentage": 0.0,
            "growth_stage": "EMPTY",
            "health": "FIELD IS EMPTY",
            "min_moisture": None,
            "max_moisture": None,
            "age_days": None,
            "harvest_days": None,
            "planted_date": None,
            "last_status_at": utc_now(),
        })
        publish_canonical_state(camp_id, "plantation", plantation, topic)
        return

    plantation["crop"] = crop_name
    plantation["crop_key"] = crop_key
    plantation["occupied"] = True
    plantation["camp_availability"] = availability if availability is not None else True
    plantation["last_status_at"] = utc_now()

    if "time_left" in detail:
        plantation["time_left"] = detail.get("time_left")
    elif "time_left" in norm:
        plantation["time_left"] = norm.get("time_left")

    if "growth_percentage" in detail:
        plantation["growth_percentage"] = detail.get("growth_percentage")
    elif "growth_percentage" in norm:
        plantation["growth_percentage"] = norm.get("growth_percentage")

    plantation["growth_stage"] = detail.get("growth_stage", norm.get("growth_stage", plantation.get("growth_stage") or "UNKNOWN"))
    plantation["health"] = detail.get("health", norm.get("health", plantation.get("health") or "UNKNOWN"))

    min_raw = detail.get("min_soilmoisture", norm.get("min_soilmoisture"))
    max_raw = detail.get("max_soilmoisture", norm.get("max_soilmoisture"))
    if min_raw is not None:
        plantation["min_moisture"] = normalize_moisture(min_raw)
    if max_raw is not None:
        plantation["max_moisture"] = normalize_moisture(max_raw)

    meta = CROPS_INFO.get(crop_name)
    if meta:
        plantation["harvest_days"] = meta["days"]
        plantation["min_moisture"] = plantation.get("min_moisture") if plantation.get("min_moisture") is not None else meta["threshold"]
        plantation["max_moisture"] = plantation.get("max_moisture") if plantation.get("max_moisture") is not None else meta["max_threshold"]

    for key in ("age_days", "harvest_days", "planted_date"):
        if key in norm and norm[key] is not None:
            plantation[key] = norm[key]

    # New backend sends time_left/growth_percentage instead of age_days.
    try:
        if plantation.get("age_days") is None and plantation.get("harvest_days") and plantation.get("time_left") is not None:
            plantation["age_days"] = max(0, float(plantation["harvest_days"]) - float(plantation["time_left"]))
    except (TypeError, ValueError):
        pass

    publish_canonical_state(camp_id, "plantation", plantation, topic)


def process_legacy_message(topic: str, payload: Any) -> None:
    topic_lower = topic.lower()

    with STATE.lock:
        STATE.mqtt["last_message_at"] = utc_now()
        STATE.mqtt["last_topic"] = topic

        manager_heartbeat = (
            topic_lower == "camp/manager/status"
            or (isinstance(payload, dict) and str(payload.get("service", "")).lower() == "camp_manager")
        )
        if manager_heartbeat and "/system/status" not in topic_lower:
            data = payload if isinstance(payload, dict) else {"status": str(payload)}
            STATE.camp_manager.update({
                "status": data.get("status", "online"),
                "service": data.get("service", "camp_manager"),
                "last_heartbeat": data.get("observed_at") or utc_now(),
                "camps": data.get("camps", []),
            })
            STATE.touch()
            return

        if "/system/status" in topic_lower:
            data = payload if isinstance(payload, dict) else {}
            camp_id = extract_camp_id(topic, data)
            if camp_id and camp_id in STATE.camps:
                sensors = data.get("sensors") if isinstance(data.get("sensors"), dict) else {}
                normalized_sensors: dict[str, dict[str, Any]] = {}
                for sensor_name in ("environment", "terrain", "plantation"):
                    sensor = sensors.get(sensor_name) if isinstance(sensors.get(sensor_name), dict) else {}
                    normalized_sensors[sensor_name] = {
                        "status": str(sensor.get("status", "UNKNOWN")).upper(),
                        "last_seen_seconds_ago": sensor.get("last_seen_seconds_ago"),
                        "latency_ms": sensor.get("latency_ms"),
                    }
                STATE.camps[camp_id]["system"] = {
                    "mqtt_connected": normalize_bool(data.get("mqtt_connected")),
                    "overall_health": str(data.get("overall_health", "UNKNOWN")).upper(),
                    "sensors": normalized_sensors,
                    "updated_at": data.get("updated_at"),
                    "received_at": utc_now(),
                }
                STATE.camps[camp_id]["last_seen"] = utc_now()
            STATE.touch()
            return

        # Camp manager publishes complete arrays for activity and harvest history.
        if "harvest" in topic_lower:
            ingest_harvest_feed(topic, payload)
            STATE.touch()
            return
        if topic_lower.startswith("activity/") or "/activity/" in topic_lower or "logs" in topic_lower:
            ingest_activity_feed(topic, payload)
            STATE.touch()
            return

        if isinstance(payload, list):
            payload = next((item for item in reversed(payload) if isinstance(item, dict)), {"value": payload})
        if not isinstance(payload, dict):
            payload = {"value": payload}

        norm = normalize_payload(payload)
        camp_id = extract_camp_id(topic, norm)
        if not camp_id:
            add_activity(topic, norm, None, "unmapped")
            STATE.touch()
            return

        camp = STATE.camps[camp_id]
        camp["last_seen"] = utc_now()
        changed_domain = False

        if "/environment/" in topic_lower or "ambient" in topic_lower or "weather" in topic_lower:
            updates = {k: v for k, v in norm.items() if k in camp["environment"] and v is not None}
            camp["environment"].update(updates)
            publish_canonical_state(camp_id, "environment", camp["environment"], topic)
            changed_domain = True

        if "/terrain/" in topic_lower or "soil_moisture" in norm or "oxygenation" in norm:
            updates = {k: v for k, v in norm.items() if k in camp["terrain"] and v is not None}
            if "soil_moisture" in updates:
                updates["soil_moisture"] = normalize_moisture(updates["soil_moisture"])
            if "irrigation_active" in updates:
                updates["irrigation_active"] = normalize_bool(updates["irrigation_active"])
            camp["terrain"].update(updates)
            publish_canonical_state(camp_id, "terrain", camp["terrain"], topic)
            changed_domain = True

        if "/plantation/" in topic_lower or "status_detail" in norm or "camp_availability" in norm or "crop" in norm or "plant" in norm:
            update_plantation_from_status(camp_id, camp, norm, topic)
            changed_domain = True

        if "camp_manager" in topic_lower or topic_lower.startswith("camp/manager/"):
            camp["manager"].update(norm)
            camp["manager"]["last_source_topic"] = topic
            publish_canonical_state(camp_id, "manager", camp["manager"], topic)
            changed_domain = True

        if not changed_domain:
            add_activity(topic, norm, camp_id, "mqtt")
        STATE.touch()


class MQTTGateway:
    def __init__(self) -> None:
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(MQTT_USER, MQTT_PASS)
        ctx = ssl.create_default_context(cafile=MQTT_CA_CERT if os.path.exists(MQTT_CA_CERT) else None)
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        self.client.tls_set_context(ctx)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    def start(self) -> None:
        try:
            self.client.connect_async(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
            self.client.loop_start()
        except Exception as exc:
            with STATE.lock:
                STATE.mqtt["last_error"] = str(exc)
                STATE.touch()

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        ok = str(reason_code).lower() in {"success", "0"}
        try:
            ok = ok or int(reason_code) == 0
        except Exception:
            pass
        with STATE.lock:
            STATE.mqtt["connected"] = ok
            STATE.mqtt["last_error"] = None if ok else str(reason_code)
            STATE.touch()
        if ok:
            for topic in (
                "camp/+/environment/telemetry",
                "camp/+/terrain/telemetry",
                "camp/+/plantation/status",
                "camp/+/system/status",
                "camp/+/camp_manager/#",
                "camp/manager/#",
                "camp/manager/status",
                "harvest/#",
                "activity/#",
            ):
                client.subscribe(topic, qos=1)

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        with STATE.lock:
            STATE.mqtt["connected"] = False
            STATE.mqtt["last_error"] = str(reason_code)
            STATE.touch()

    def on_message(self, client, userdata, msg):
        try:
            text = msg.payload.decode("utf-8")
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {"value": text}
            process_legacy_message(msg.topic, payload)
        except Exception as exc:
            with STATE.lock:
                STATE.mqtt["last_error"] = str(exc)
                STATE.touch()

    def publish(self, topic: str, payload: str, qos: int = 1, retain: bool = False):
        return self.client.publish(topic, payload, qos=qos, retain=retain)

    def dispatch(self, camp_id: str, action: str, params: dict[str, Any]) -> dict[str, Any]:
        if camp_id not in CAMPS:
            raise ValueError("unknown camp_id")
        if action not in ACTIONS:
            raise ValueError("unsupported action")

        cmd = command_envelope(camp_id, action, params)
        legacy = to_legacy_command(camp_id, action, params)
        self.publish(command_topic(camp_id, action), json.dumps(cmd, ensure_ascii=False), qos=1, retain=False)
        info = self.publish(legacy.topic, legacy.payload, qos=1, retain=False)

        status = "accepted" if info.rc == mqtt.MQTT_ERR_SUCCESS else "publish_error"
        ack = ack_envelope(cmd, status, detail=f"legacy_topic={legacy.topic}")
        self.publish(cmd["reply_to"], json.dumps(ack, ensure_ascii=False), qos=1, retain=False)

        with STATE.lock:
            STATE.commands.append({
                **cmd,
                "gateway_status": status,
                "legacy_topic": legacy.topic,
                "legacy_payload": legacy.payload,
            })
            add_activity(command_topic(camp_id, action), cmd, camp_id, "command")
            STATE.touch()
        return {"command": cmd, "ack": ack}


MQTT = MQTTGateway()


def crop_payload() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "key": meta["key"],
            "min_moisture": meta["threshold"],
            "max_moisture": meta["max_threshold"],
            "min_temp": meta["min_temp"],
            "max_temp": meta["max_temp"],
            "ideal_soil": meta["ideal_soil"],
            "days": meta["days"],
            "seasons": meta["seasons"],
        }
        for name, meta in CROPS_INFO.items()
    ]


class WebHandler(BaseHTTPRequestHandler):
    server_version = "SmartFarmGateway/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[HTTP] {self.address_string()} - {fmt % args}", flush=True)

    def _json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, content_type: str | None = None) -> None:
        try:
            resolved = path.resolve(strict=True)
            if resolved != INDEX_FILE.resolve() and STATIC_DIR.resolve() not in resolved.parents:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            body = resolved.read_bytes()
        except (FileNotFoundError, OSError):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or mimetypes.guess_type(str(resolved))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _body_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (ValueError, json.JSONDecodeError):
            return {}

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            return self._file(INDEX_FILE, "text/html; charset=utf-8")
        if path.startswith("/static/"):
            rel = path.removeprefix("/static/")
            return self._file(STATIC_DIR / rel)
        if path == "/api/state":
            return self._json(STATE.snapshot())
        if path == "/api/crops":
            return self._json({"crops": crop_payload(), "soil_types": SOIL_TYPES})
        if path in {"/healthz", "/_stcore/health"}:
            snapshot = STATE.snapshot()
            return self._json({
                "ok": True,
                "mqtt_connected": snapshot["mqtt"]["connected"],
                "camp_manager_connected": snapshot["camp_manager"]["connected"],
            })
        if path == "/_stcore/host-config":
            return self._json({"allowedOrigins": [], "useExternalAuthToken": False})
        if path == "/api/events":
            return self._events()
        self.send_error(HTTPStatus.NOT_FOUND)

    def _events(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        last_revision = -1
        try:
            while True:
                with STATE.changed:
                    STATE.changed.wait_for(lambda: STATE.revision != last_revision, timeout=15)
                    snapshot = STATE.snapshot()
                    last_revision = snapshot["revision"]
                frame = f"event: state\ndata: {json.dumps(snapshot, ensure_ascii=False)}\n\n".encode("utf-8")
                self.wfile.write(frame)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        parts = [p for p in path.split("/") if p]
        if len(parts) == 5 and parts[:2] == ["api", "camps"] and parts[3] == "commands":
            camp_id, action = parts[2], parts[4]
            try:
                result = MQTT.dispatch(camp_id, action, self._body_json())
                return self._json(result, HTTPStatus.ACCEPTED)
            except (ValueError, TypeError) as exc:
                return self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        self.send_error(HTTPStatus.NOT_FOUND)


def run() -> None:
    MQTT.start()
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), WebHandler)
    print(f"Smart Farm web gateway listening on http://0.0.0.0:{PORT}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        MQTT.client.loop_stop()
        MQTT.client.disconnect()


if __name__ == "__main__":
    run()
