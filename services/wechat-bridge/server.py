#!/usr/bin/env python
"""HTTP API for the read-only PC WeChat sidecar."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from bridge import BridgeRuntime
from ocr_monitor import OcrMonitor
from wechat_probe import probe_weixin


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = BridgeRuntime(ROOT / "data" / "generated" / "wechat-bridge")
MONITOR = OcrMonitor(RUNTIME, ROOT / "data" / "generated" / "wechat-bridge")
ALLOWED_DASHBOARD_ORIGINS = {
    "http://127.0.0.1:8788",
    "http://127.0.0.1:8789",
    "http://localhost:8788",
    "http://localhost:8789",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "DigitalTwinWeChatBridge/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/api/health"}:
            self.send_json({"ok": True, "service": "wechat-bridge", "auto_send": False})
        elif parsed.path == "/api/status":
            self.send_json({"ok": True, "status": {**RUNTIME.status(), "monitor": MONITOR.status()}})
        elif parsed.path == "/api/events":
            group = (parse_qs(parsed.query).get("group") or [""])[0]
            self.send_json({"ok": True, "events": RUNTIME.events(group)})
        elif parsed.path == "/api/reviews":
            self.send_json({"ok": True, "reviews": [item.__dict__ for item in RUNTIME.reviews]})
        elif parsed.path == "/api/wechat/probe":
            self.send_json({"ok": True, "probe": probe_weixin()})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        try:
            payload = self.read_json()
            handlers = {
                "/api/watch/start": lambda: self.start_watch(payload),
                "/api/watch/stop": self.stop_watch,
                "/api/model/config": lambda: RUNTIME.configure_model(payload),
                "/api/events": lambda: RUNTIME.ingest(payload),
                "/api/reviews/generate": lambda: RUNTIME.generate_review(payload),
                "/api/reviews/decision": lambda: RUNTIME.decide_review(payload),
            }
            handler = handlers.get(urlparse(self.path).path)
            if handler is None:
                self.send_error(404)
                return
            self.send_json({"ok": True, "result": handler()})
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=400)

    def start_watch(self, payload: dict[str, Any]) -> dict[str, Any]:
        status = RUNTIME.start(payload)
        if RUNTIME.adapter == "window_capture_ocr":
            MONITOR.start()
        return status

    def stop_watch(self) -> dict[str, Any]:
        MONITOR.stop()
        return RUNTIME.stop()

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_cors_headers(self) -> None:
        origin = self.headers.get("Origin", "")
        allowed_origin = origin if origin in ALLOWED_DASHBOARD_ORIGINS else "http://127.0.0.1:8788"
        self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Vary", "Origin")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the read-only WeChat bridge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"WeChat bridge listening on http://{args.host}:{args.port}/ (auto_send=false)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
