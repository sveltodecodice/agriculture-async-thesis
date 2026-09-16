"""Minimal HTTP + SSE server for the dashboard frontend."""
from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from config import CAMPS, HTTP_PORT
from mqtt_contract import SUPPORTED_ACTIONS
from mqtt_service import MQTT
from seeds import CROPS_INFO
from state_store import STATE

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = BASE_DIR / "templates" / "index.html"


def crops_payload() -> list[dict[str, Any]]:
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
    server_version = "SmartFarmStudentDashboard/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[HTTP] {self.address_string()} - {fmt % args}", flush=True)

    def _json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
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

    def _body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            decoded = json.loads(self.rfile.read(length).decode("utf-8"))
            return decoded if isinstance(decoded, dict) else {}
        except (ValueError, json.JSONDecodeError):
            return {}

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            return self._file(INDEX_FILE, "text/html; charset=utf-8")
        if path.startswith("/static/"):
            return self._file(STATIC_DIR / path.removeprefix("/static/"))
        if path == "/api/state":
            return self._json(STATE.snapshot())
        if path == "/api/crops":
            return self._json({"crops": crops_payload()})
        if path == "/api/events":
            return self._events()
        if path in {"/healthz", "/_stcore/health"}:
            snap = STATE.snapshot()
            return self._json({
                "ok": True,
                "mqtt_connected": snap["mqtt"]["connected"],
                "camp_manager_connected": snap["camp_manager"]["connected"],
            })
        if path == "/_stcore/host-config":
            return self._json({"allowedOrigins": [], "useExternalAuthToken": False})
        self.send_error(HTTPStatus.NOT_FOUND)

    def _events(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        revision = -1
        try:
            while True:
                with STATE.changed:
                    STATE.changed.wait_for(lambda: STATE.revision != revision, timeout=15)
                    snap = STATE.snapshot()
                    revision = snap["revision"]
                self.wfile.write(f"event: state\ndata: {json.dumps(snap, ensure_ascii=False)}\n\n".encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_POST(self) -> None:
        parts = [p for p in urlparse(self.path).path.split("/") if p]
        # POST /api/camps/field_a/commands/irrigate
        if len(parts) == 5 and parts[:2] == ["api", "camps"] and parts[3] == "commands":
            camp_id, action = parts[2], parts[4]
            if camp_id not in CAMPS or action not in SUPPORTED_ACTIONS:
                return self._json({"error": "unsupported camp or action"}, HTTPStatus.BAD_REQUEST)
            try:
                return self._json(MQTT.send_command(camp_id, action, self._body()), HTTPStatus.ACCEPTED)
            except (ValueError, TypeError) as exc:
                return self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        self.send_error(HTTPStatus.NOT_FOUND)


def run_http_server() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    print(f"Smart Farm dashboard listening on http://0.0.0.0:{HTTP_PORT}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
