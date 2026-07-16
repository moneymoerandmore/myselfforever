#!/usr/bin/env python
"""Local bridge contract for the persistent 3D avatar runtime."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime
import hashlib
import json
import os
import secrets
import socket
import ssl
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4


STATE: dict[str, Any] = {
    "state": "idle",
    "runtime_connected": False,
    "provider": "web_threejs_runtime",
    "character_id": "digital_twin_3d",
    "last_command": None,
    "last_unreal_event": None,
    "updated_at": None,
}
EVENT_QUEUE: list[dict[str, Any]] = []
EVENT_CONDITION = threading.Condition()
MAX_EVENT_QUEUE = 200
LAST_UNREAL_PULL_AT = 0.0


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def runtime_connected() -> bool:
    if os.environ.get("AVATAR3D_RUNTIME_CONNECTED", "").strip().lower() in {"1", "true", "yes"}:
        return True
    last_unreal = STATE.get("last_unreal_event")
    if isinstance(last_unreal, dict) and last_unreal.get("ok"):
        return True
    return time.time() - LAST_UNREAL_PULL_AT < 10.0


def unreal_ws_url(payload: dict[str, Any] | None = None) -> str:
    payload_url = str((payload or {}).get("unreal_ws_url") or "").strip()
    return (
        payload_url
        or os.environ.get("UNREAL_WS_URL", "").strip()
        or os.environ.get("AVATAR3D_UNREAL_WS_URL", "").strip()
    )


def public_state() -> dict[str, Any]:
    pull_url = "/api/unreal/events"
    STATE["runtime_connected"] = runtime_connected()
    STATE["provider"] = os.environ.get("AVATAR3D_PROVIDER", "").strip() or STATE["provider"]
    STATE["character_id"] = os.environ.get("AVATAR3D_CHARACTER_ID", "").strip() or STATE["character_id"]
    state = dict(STATE)
    state["unreal"] = {
        "configured": bool(unreal_ws_url()),
        "ws_url": unreal_ws_url(),
        "pull_url": pull_url,
        "pull_connected": time.time() - LAST_UNREAL_PULL_AT < 10.0,
        "queued_events": len(EVENT_QUEUE),
        "last_event": STATE.get("last_unreal_event"),
    }
    return state


def enqueue_unreal_event(event: dict[str, Any]) -> dict[str, Any]:
    event = dict(event)
    event["event_id"] = uuid4().hex
    with EVENT_CONDITION:
        EVENT_QUEUE.append(event)
        if len(EVENT_QUEUE) > MAX_EVENT_QUEUE:
            del EVENT_QUEUE[: len(EVENT_QUEUE) - MAX_EVENT_QUEUE]
        EVENT_CONDITION.notify_all()
    return event


def unreal_events_after(after: str, timeout_seconds: float) -> list[dict[str, Any]]:
    global LAST_UNREAL_PULL_AT
    deadline = time.time() + max(0.0, min(timeout_seconds, 15.0))
    with EVENT_CONDITION:
        while True:
            LAST_UNREAL_PULL_AT = time.time()
            if not after:
                events = EVENT_QUEUE[-20:]
            else:
                index = next((idx for idx, event in enumerate(EVENT_QUEUE) if event.get("event_id") == after), -1)
                events = EVENT_QUEUE[index + 1 :] if index >= 0 else EVENT_QUEUE[-20:]
            if events or time.time() >= deadline:
                return [dict(event) for event in events]
            EVENT_CONDITION.wait(timeout=max(0.05, deadline - time.time()))


class MinimalWebSocketTextClient:
    def __init__(self, url: str, timeout: float = 1.5):
        self.url = url
        self.timeout = timeout
        self.sock: socket.socket | ssl.SSLSocket | None = None

    def __enter__(self) -> "MinimalWebSocketTextClient":
        parsed = urlparse(self.url)
        if parsed.scheme not in {"ws", "wss"}:
            raise ValueError("Unreal websocket URL must start with ws:// or wss://")
        host = parsed.hostname
        if not host:
            raise ValueError("Unreal websocket URL host is required")
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        raw_sock = socket.create_connection((host, port), timeout=self.timeout)
        raw_sock.settimeout(self.timeout)
        if parsed.scheme == "wss":
            context = ssl.create_default_context()
            self.sock = context.wrap_socket(raw_sock, server_hostname=host)
        else:
            self.sock = raw_sock
        self._handshake(parsed, host, port)
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            self._send_frame(0x8, b"")
        except Exception:
            pass
        if self.sock:
            self.sock.close()

    def _handshake(self, parsed: Any, host: str, port: int) -> None:
        if not self.sock:
            raise RuntimeError("websocket socket is not open")
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        host_header = host if parsed.port is None else f"{host}:{port}"
        request_text = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.sock.sendall(request_text.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if len(response) > 16384:
                break
        header_text = response.decode("iso-8859-1", errors="replace")
        if " 101 " not in header_text.split("\r\n", 1)[0]:
            raise RuntimeError("Unreal websocket handshake failed")
        expected_accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if expected_accept not in header_text:
            raise RuntimeError("Unreal websocket accept key mismatch")

    def send_json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_frame(0x1, body)

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        if not self.sock:
            raise RuntimeError("websocket socket is not open")
        first = 0x80 | opcode
        length = len(payload)
        mask_bit = 0x80
        if length < 126:
            header = struct.pack("!BB", first, mask_bit | length)
        elif length <= 0xFFFF:
            header = struct.pack("!BBH", first, mask_bit | 126, length)
        else:
            header = struct.pack("!BBQ", first, mask_bit | 127, length)
        mask = secrets.token_bytes(4)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(header + mask + masked)


def forward_unreal_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = unreal_ws_url(payload)
    event = {
        "type": event_type,
        "sent_at": now_iso(),
        "provider": STATE["provider"],
        "character_id": str(payload.get("character_id") or STATE["character_id"]).strip(),
        "payload": payload,
    }
    event = enqueue_unreal_event(event)
    if not url:
        result = {
            "configured": False,
            "ok": False,
            "event_type": event_type,
            "event_id": event["event_id"],
            "queued": True,
            "error": "UNREAL_WS_URL is not configured; event queued for HTTP pull",
        }
        STATE["last_unreal_event"] = result
        return result
    try:
        with MinimalWebSocketTextClient(url, timeout=1.5) as ws:
            ws.send_json(event)
        result = {"configured": True, "ok": True, "ws_url": url, "event_type": event_type, "event_id": event["event_id"], "queued": True}
    except Exception as exc:
        result = {
            "configured": True,
            "ok": False,
            "ws_url": url,
            "event_type": event_type,
            "event_id": event["event_id"],
            "queued": True,
            "error": str(exc),
        }
    STATE["last_unreal_event"] = result
    return result


class Avatar3DBridgeHandler(BaseHTTPRequestHandler):
    server_version = "Avatar3DBridge/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/health":
            self.send_json({"ok": True, **public_state()})
            return
        if path == "/api/state":
            self.send_json({"ok": True, "result": public_state()})
            return
        if path == "/api/unreal/events":
            after = str((query.get("after") or [""])[0]).strip()
            timeout = float((query.get("timeout") or ["0"])[0] or 0)
            events = unreal_events_after(after, timeout)
            self.send_json(
                {
                    "ok": True,
                    "result": {
                        "events": events,
                        "last_event_id": events[-1]["event_id"] if events else after,
                        "state": public_state(),
                    },
                }
            )
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/api/state", "/api/say", "/api/unreal/ack"}:
            self.send_error(404)
            return
        try:
            payload = self.read_json()
            if path == "/api/state":
                result = self.set_state(payload)
            elif path == "/api/unreal/ack":
                result = self.ack_unreal(payload)
            else:
                result = self.say(payload)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=400)
            return
        self.send_json({"ok": True, "result": result})

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        if not raw:
            return {}
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON object is required")
        return payload

    def set_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = str(payload.get("state") or "").strip()
        if state not in {"idle", "listening", "thinking", "speaking", "error"}:
            raise ValueError("state must be idle/listening/thinking/speaking/error")
        STATE["state"] = state
        STATE["updated_at"] = now_iso()
        unreal_event = forward_unreal_event("state", {"state": state, **payload})
        return {**public_state(), "unreal_event": unreal_event}

    def say(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text") or "").strip()
        if not text:
            raise ValueError("text is required")
        command = {
            "id": uuid4().hex,
            "created_at": now_iso(),
            "text": text,
            "audio_url": str(payload.get("audio_url") or "").strip(),
            "audio_chunks": payload.get("audio_chunks") if isinstance(payload.get("audio_chunks"), list) else [],
            "audio_format": str(payload.get("audio_format") or "").strip(),
            "voice_provider": str(payload.get("voice_provider") or "").strip(),
            "character_id": str(payload.get("character_id") or STATE["character_id"]).strip(),
            "metadata": payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
            "unreal_ws_url": unreal_ws_url(payload),
        }
        STATE["last_command"] = command
        STATE["updated_at"] = now_iso()
        unreal_event = forward_unreal_event("say", command)
        STATE["state"] = "speaking" if unreal_event.get("ok") or runtime_connected() else "idle"
        return {
            **public_state(),
            "accepted": True,
            "command_id": command["id"],
            "unreal_event": unreal_event,
            "note": "No real 3D runtime is attached yet." if not runtime_connected() else "",
        }

    def ack_unreal(self, payload: dict[str, Any]) -> dict[str, Any]:
        global LAST_UNREAL_PULL_AT
        LAST_UNREAL_PULL_AT = time.time()
        event_id = str(payload.get("event_id") or "").strip()
        STATE["last_unreal_ack"] = {
            "event_id": event_id,
            "received_at": now_iso(),
            "status": str(payload.get("status") or "ok").strip(),
        }
        return public_state()

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local 3D avatar bridge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8820, type=int)
    parser.add_argument("--unreal-ws-url", default="", help="Optional Unreal websocket endpoint, e.g. ws://127.0.0.1:8830/avatar")
    args = parser.parse_args()
    if args.unreal_ws_url:
        os.environ["UNREAL_WS_URL"] = args.unreal_ws_url
    server = ThreadingHTTPServer((args.host, args.port), Avatar3DBridgeHandler)
    print(f"Avatar 3D bridge listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
