#!/usr/bin/env python
"""Launch the WeChat bridge as a detached local Windows process."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = Path(__file__).resolve().parent
PID_FILE = SERVICE_DIR / "wechat-bridge.pid"
LOG_FILE = SERVICE_DIR / "wechat-bridge.log"
ERR_FILE = SERVICE_DIR / "wechat-bridge.err.log"


def main() -> int:
    host = "127.0.0.1"
    port = "8790"
    command = [sys.executable, str(SERVICE_DIR / "server.py"), "--host", host, "--port", port]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    with LOG_FILE.open("ab") as stdout, ERR_FILE.open("ab") as stderr:
        process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            env=env,
            close_fds=True,
            creationflags=creationflags,
        )
    PID_FILE.write_text(str(process.pid), encoding="utf-8")
    print(f"WeChat bridge pid={process.pid} url=http://{host}:{port}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
