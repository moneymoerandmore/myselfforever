#!/usr/bin/env python
"""Tiny websocket receiver that mimics the Unreal command endpoint."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import socketserver
import struct
from typing import Any


GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class MockUnrealWebSocketHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        headers = self.read_headers()
        key = headers.get("sec-websocket-key", "")
        if not key:
            return
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode("ascii")).digest()).decode("ascii")
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        self.request.sendall(response.encode("ascii"))
        while True:
            message = self.read_text_frame()
            if message is None:
                return
            try:
                payload: Any = json.loads(message)
            except json.JSONDecodeError:
                payload = message
            print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)

    def read_headers(self) -> dict[str, str]:
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = self.request.recv(4096)
            if not chunk:
                break
            raw += chunk
            if len(raw) > 16384:
                break
        lines = raw.decode("iso-8859-1", errors="replace").split("\r\n")
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()
        return headers

    def read_exact(self, length: int) -> bytes:
        chunks: list[bytes] = []
        remaining = length
        while remaining > 0:
            chunk = self.request.recv(remaining)
            if not chunk:
                raise ConnectionError("client disconnected")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def read_text_frame(self) -> str | None:
        try:
            header = self.read_exact(2)
        except ConnectionError:
            return None
        first, second = header
        opcode = first & 0x0F
        if opcode == 0x8:
            return None
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self.read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self.read_exact(8))[0]
        mask = self.read_exact(4) if masked else b""
        payload = self.read_exact(length)
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        if opcode != 0x1:
            return ""
        return payload.decode("utf-8", errors="replace")


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a mock Unreal websocket endpoint.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8830, type=int)
    args = parser.parse_args()
    server = ReusableTCPServer((args.host, args.port), MockUnrealWebSocketHandler)
    print(f"Mock Unreal websocket listening on ws://{args.host}:{args.port}/avatar")
    server.serve_forever()


if __name__ == "__main__":
    main()
