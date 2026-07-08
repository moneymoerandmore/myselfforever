#!/usr/bin/env python
"""Persistent IndexTTS2 HTTP worker for the avatar layer."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
from typing import Any


class IndexTTS2Worker:
    def __init__(
        self,
        repo: Path,
        voice: Path,
        *,
        fp16: bool = True,
        cuda_kernel: bool = False,
        deepspeed: bool = False,
    ) -> None:
        self.repo = repo.resolve()
        self.voice = voice.resolve()
        self.cfg_path = self.repo / "checkpoints" / "config.yaml"
        self.model_dir = self.repo / "checkpoints"
        self.lock = threading.Lock()
        self.started_at = time.time()

        if not self.repo.exists():
            raise FileNotFoundError(f"IndexTTS repo not found: {self.repo}")
        if not self.cfg_path.exists():
            raise FileNotFoundError(f"IndexTTS config not found: {self.cfg_path}")
        if not self.voice.exists():
            raise FileNotFoundError(f"speaker reference audio not found: {self.voice}")

        sys.path.insert(0, str(self.repo))
        from indextts.infer_v2 import IndexTTS2  # type: ignore

        load_started = time.time()
        self.tts = IndexTTS2(
            cfg_path=str(self.cfg_path),
            model_dir=str(self.model_dir),
            use_fp16=fp16,
            use_cuda_kernel=cuda_kernel,
            use_deepspeed=deepspeed,
        )
        self.load_seconds = round(time.time() - load_started, 2)

    def synthesize(
        self,
        text_path: Path,
        audio_path: Path,
        *,
        emotion_audio: str = "",
        emotion_text: str = "",
        emotion_alpha: float = 0.6,
        verbose: bool = False,
    ) -> dict[str, Any]:
        text = text_path.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError("input text is empty")
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        kwargs: dict[str, Any] = {
            "spk_audio_prompt": str(self.voice),
            "text": text,
            "output_path": str(audio_path),
            "verbose": verbose,
        }
        if emotion_audio:
            kwargs["emo_audio_prompt"] = str(Path(emotion_audio).resolve())
            kwargs["emo_alpha"] = emotion_alpha
        elif emotion_text:
            kwargs["use_emo_text"] = True
            kwargs["emo_text"] = emotion_text
            kwargs["emo_alpha"] = emotion_alpha

        started = time.time()
        # IndexTTS2 is not guaranteed to be thread-safe, so serialize requests.
        with self.lock:
            self.tts.infer(**kwargs)
        if not audio_path.exists():
            raise FileNotFoundError(f"IndexTTS2 did not create output wav: {audio_path}")
        return {
            "audio_path": str(audio_path),
            "text_chars": len(text),
            "inference_seconds": round(time.time() - started, 2),
            "model_load_seconds": self.load_seconds,
            "uptime_seconds": round(time.time() - self.started_at, 2),
        }


class WorkerHandler(BaseHTTPRequestHandler):
    server_version = "IndexTTS2Worker/0.1"
    worker: IndexTTS2Worker

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_json(
            {
                "ok": True,
                "provider": "indextts2",
                "model_loaded": True,
                "model_load_seconds": self.worker.load_seconds,
                "uptime_seconds": round(time.time() - self.worker.started_at, 2),
            }
        )

    def do_POST(self) -> None:
        if self.path != "/tts":
            self.send_error(404)
            return
        try:
            payload = self.read_json()
            result = self.worker.synthesize(
                Path(str(payload.get("text_path") or "")).resolve(),
                Path(str(payload.get("audio_path") or "")).resolve(),
                emotion_audio=str(payload.get("emotion_audio") or ""),
                emotion_text=str(payload.get("emotion_text") or ""),
                emotion_alpha=float(payload.get("emotion_alpha") or 0.6),
                verbose=bool(payload.get("verbose", False)),
            )
            self.send_json({"ok": True, "result": result})
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=400)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body or "{}")
        if not isinstance(payload, dict):
            raise ValueError("JSON object expected")
        return payload

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run persistent IndexTTS2 worker.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8811)
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--cuda-kernel", action="store_true")
    parser.add_argument("--deepspeed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    WorkerHandler.worker = IndexTTS2Worker(
        Path(args.repo),
        Path(args.voice),
        fp16=args.fp16,
        cuda_kernel=args.cuda_kernel,
        deepspeed=args.deepspeed,
    )
    server = ThreadingHTTPServer((args.host, args.port), WorkerHandler)
    print(f"IndexTTS2 worker listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping IndexTTS2 worker.", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
