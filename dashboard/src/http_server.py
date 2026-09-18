"""Minimal HTTP server: static UI, JSON state, crop catalog and commands."""
from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from config import CAMPS, DASHBOARD_POLL_INTERVAL_SECONDS, HTTP_PORT
from mqtt_contract import SUPPORTED_ACTIONS
from mqtt_service import MQTT
from seeds import CROPS_INFO
from state_store import STATE

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "static"
INDEX = BASE / "templates" / "index.html"


def crop_list() -> list[dict[str, Any]]:
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


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[HTTP] {fmt % args}", flush=True)

    def json_response(self, data: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def file_response(self, path: Path, content_type: str | None = None) -> None:
        try:
            path = path.resolve(strict=True)
            if path != INDEX.resolve() and STATIC.resolve() not in path.parents:
                return self.send_error(HTTPStatus.FORBIDDEN)
            body = path.read_bytes()
        except OSError:
            return self.send_error(HTTPStatus.NOT_FOUND)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def body_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", 0))
            value = json.loads(self.rfile.read(length).decode()) if length else {}
            return value if isinstance(value, dict) else {}
        except (ValueError, json.JSONDecodeError):
            return {}

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            return self.file_response(INDEX, "text/html; charset=utf-8")
        if path == "/static/app.js":
            return self.file_response(STATIC / "app.js", "text/javascript; charset=utf-8")
        if path == "/static/styles.css":
            return self.file_response(STATIC / "styles.css", "text/css; charset=utf-8")
        if path == "/api/state":
            return self.json_response(STATE.snapshot())
        if path == "/api/crops":
            return self.json_response({"crops": crop_list()})
        if path == "/api/config":
            return self.json_response({"polling_interval_seconds": DASHBOARD_POLL_INTERVAL_SECONDS})
        if path == "/healthz":
            snap = STATE.snapshot()
            return self.json_response({"ok": True, "mqtt_connected": snap["mqtt"]["connected"]})
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parts = [part for part in urlparse(self.path).path.split("/") if part]
        if len(parts) == 5 and parts[:2] == ["api", "camps"] and parts[3] == "commands":
            camp_id, action = parts[2], parts[4]
            if camp_id not in CAMPS or action not in SUPPORTED_ACTIONS:
                return self.json_response({"error": "Campo o comando non supportato"}, HTTPStatus.BAD_REQUEST)
            try:
                result = MQTT.send_command(camp_id, action, self.body_json())
                return self.json_response(result, HTTPStatus.ACCEPTED)
            except (ValueError, TypeError) as exc:
                return self.json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except ConnectionError as exc:
                return self.json_response({"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
        self.send_error(HTTPStatus.NOT_FOUND)


def run_http_server() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    print(f"Dashboard Smart Farm disponibile su http://0.0.0.0:{HTTP_PORT}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
