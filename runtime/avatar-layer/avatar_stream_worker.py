from __future__ import annotations

import argparse
import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import cv2


STARTED_AT = time.time()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Loop an avatar idle video as an MJPEG stream.")
    parser.add_argument("--video", required=True, help="Path to the idle video to loop.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8813)
    parser.add_argument("--fps", type=float, default=12.0)
    parser.add_argument("--jpeg-quality", type=int, default=82)
    return parser.parse_args()


class StreamState:
    def __init__(self, video_path: Path, fps: float, jpeg_quality: int) -> None:
        self.video_path = video_path
        self.fps = max(1.0, fps)
        self.jpeg_quality = max(40, min(95, jpeg_quality))
        self.lock = threading.Lock()
        self.active_video_path: Path | None = None
        self.active_token = 0
        self.active_started_at: float | None = None
        self.active_frame: bytes | None = None
        self.active_frame_token = 0
        self.active_frame_count = 0
        self.active_frame_started_at: float | None = None
        self.active_frame_updated_at: float | None = None

    def health(self) -> dict[str, Any]:
        with self.lock:
            active_video_path = self.active_video_path
            active_token = self.active_token
            active_started_at = self.active_started_at
            active_frame_count = self.active_frame_count
            active_frame_token = self.active_frame_token
            active_frame_started_at = self.active_frame_started_at
            active_frame_updated_at = self.active_frame_updated_at
        return {
            "ok": self.video_path.exists(),
            "provider": "avatar_idle_stream",
            "mode": "mjpeg",
            "source_video": str(self.video_path),
            "source_exists": self.video_path.exists(),
            "active_video": str(active_video_path) if active_video_path else "",
            "active_token": active_token,
            "active_elapsed_seconds": round(time.time() - active_started_at, 2)
            if active_started_at
            else 0,
            "active_frame_token": active_frame_token,
            "active_frame_count": active_frame_count,
            "active_frame_elapsed_seconds": round(time.time() - active_frame_started_at, 2)
            if active_frame_started_at
            else 0,
            "active_frame_age_seconds": round(time.time() - active_frame_updated_at, 2)
            if active_frame_updated_at
            else 0,
            "fps": self.fps,
            "jpeg_quality": self.jpeg_quality,
            "uptime_seconds": round(time.time() - STARTED_AT, 2),
        }

    def source(self) -> tuple[Path, int, bool]:
        with self.lock:
            if self.active_video_path:
                return self.active_video_path, self.active_token, True
            return self.video_path, self.active_token, False

    def play_video(self, video_path: Path) -> dict[str, Any]:
        if not video_path.exists():
            raise FileNotFoundError(f"video not found: {video_path}")
        with self.lock:
            self.active_video_path = video_path
            self.active_token += 1
            self.active_started_at = time.time()
            return {
                "ok": True,
                "mode": "speaking_clip",
                "video_path": str(video_path),
                "active_token": self.active_token,
            }

    def finish_active(self, token: int) -> None:
        with self.lock:
            if self.active_token == token:
                self.active_video_path = None
                self.active_started_at = None

    def push_frame(self, frame: bytes) -> dict[str, Any]:
        if not frame:
            raise ValueError("empty frame")
        with self.lock:
            if self.active_frame is None:
                self.active_frame_token += 1
                self.active_frame_count = 0
                self.active_frame_started_at = time.time()
            self.active_frame = frame
            self.active_frame_count += 1
            self.active_frame_updated_at = time.time()
            return {
                "ok": True,
                "mode": "speaking_frames",
                "active_frame_token": self.active_frame_token,
                "active_frame_count": self.active_frame_count,
            }

    def frame(self) -> tuple[bytes | None, int]:
        with self.lock:
            if self.active_frame and self.active_frame_updated_at:
                if time.time() - self.active_frame_updated_at <= 2.0:
                    return self.active_frame, self.active_frame_token
                self.active_frame = None
                self.active_frame_started_at = None
                self.active_frame_updated_at = None
            return None, self.active_frame_token


class AvatarStreamHandler(BaseHTTPRequestHandler):
    server_version = "AvatarStreamWorker/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    @property
    def state(self) -> StreamState:
        return self.server.state  # type: ignore[attr-defined]

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            status = HTTPStatus.OK if self.state.video_path.exists() else HTTPStatus.SERVICE_UNAVAILABLE
            self.send_json(self.state.health(), status)
            return
        if path == "/idle.mjpg":
            self.serve_mjpeg()
            return
        self.send_json({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/push-frame":
            try:
                length = int(self.headers.get("Content-Length") or 0)
                self.send_json(self.state.push_frame(self.rfile.read(length)))
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path != "/play-video":
            self.send_json({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            video_path = Path(str(payload.get("video_path") or "")).resolve()
            self.send_json(self.state.play_video(video_path))
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def serve_mjpeg(self) -> None:
        if not self.state.video_path.exists():
            self.send_json({"ok": False, "error": "idle video not found"}, HTTPStatus.NOT_FOUND)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=avatarframe")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        frame_interval = 1.0 / self.state.fps
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.state.jpeg_quality]
        capture: Any = None
        current_path: Path | None = None
        current_token = -1
        current_active = False
        try:
            while True:
                active_frame, _frame_token = self.state.frame()
                if active_frame:
                    self.wfile.write(b"--avatarframe\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(active_frame)}\r\n\r\n".encode("ascii"))
                    self.wfile.write(active_frame)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                    time.sleep(frame_interval)
                    continue

                target_path, target_token, target_active = self.state.source()
                if target_path != current_path or target_token != current_token:
                    if capture is not None:
                        capture.release()
                    capture = cv2.VideoCapture(str(target_path))
                    current_path = target_path
                    current_token = target_token
                    current_active = target_active

                ok, frame = capture.read()
                if not ok:
                    capture.release()
                    if current_active:
                        self.state.finish_active(current_token)
                        current_path = None
                        current_token = -1
                        current_active = False
                        continue
                    capture = cv2.VideoCapture(str(target_path))
                    ok, frame = capture.read()
                    if not ok:
                        time.sleep(0.25)
                        continue

                encoded_ok, encoded = cv2.imencode(".jpg", frame, encode_params)
                if not encoded_ok:
                    continue

                payload = encoded.tobytes()
                self.wfile.write(b"--avatarframe\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii"))
                self.wfile.write(payload)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
                time.sleep(frame_interval)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return
        finally:
            if capture is not None:
                capture.release()


class AvatarStreamServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], state: StreamState) -> None:
        super().__init__(server_address, AvatarStreamHandler)
        self.state = state


def main() -> None:
    args = parse_args()
    state = StreamState(Path(args.video), args.fps, args.jpeg_quality)
    server = AvatarStreamServer((args.host, args.port), state)
    print(
        json.dumps(
            {
                "ok": True,
                "url": f"http://{args.host}:{args.port}",
                "idle_stream": f"http://{args.host}:{args.port}/idle.mjpg",
                "video": str(state.video_path),
                "fps": state.fps,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
