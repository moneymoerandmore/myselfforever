#!/usr/bin/env python
"""Thin adapter from the digital twin avatar contract to local LivePortrait."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4


DEFAULT_FFMPEG_DIR = (
    r"C:\Users\cloud\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1.2-full_build\bin"
)


def run(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    print(">>", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=str(cwd), env=env)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with exit code {completed.returncode}")


def newest_video(output_dir: Path) -> Path:
    candidates = [
        path
        for path in output_dir.glob("*.mp4")
        if not path.name.endswith("_concat.mp4")
    ]
    if not candidates:
        candidates = list(output_dir.glob("*.mp4"))
    if not candidates:
        raise FileNotFoundError(f"LivePortrait did not create an mp4 in {output_dir}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Path to the LivePortrait repository.")
    parser.add_argument("--image", required=True, help="Source portrait image.")
    parser.add_argument("--audio", required=True, help="Reply audio wav.")
    parser.add_argument("--out", required=True, help="Final mp4 output path.")
    parser.add_argument("--driving", default="", help="Driving video or template. Defaults to assets/examples/driving/d0.pkl.")
    parser.add_argument("--ffmpeg-dir", default=DEFAULT_FFMPEG_DIR)
    parser.add_argument("--no-half", action="store_true", help="Disable LivePortrait fp16.")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    source_image = Path(args.image).resolve()
    source_audio = Path(args.audio).resolve()
    output_path = Path(args.out).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not repo.exists():
        raise FileNotFoundError(f"LivePortrait repo not found: {repo}")
    if not source_image.exists():
        raise FileNotFoundError(f"source image not found: {source_image}")
    if not source_audio.exists():
        raise FileNotFoundError(f"audio not found: {source_audio}")

    driving = Path(args.driving).resolve() if args.driving else repo / "assets" / "examples" / "driving" / "d0.pkl"
    if not driving.exists():
        driving = repo / "assets" / "examples" / "driving" / "d0.mp4"
    if not driving.exists():
        raise FileNotFoundError(f"driving file not found: {driving}")

    work_dir = repo / "digital_twin_jobs" / f"{output_path.parent.name}-{uuid4().hex[:8]}"
    input_dir = work_dir / "input"
    raw_dir = work_dir / "raw"
    input_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    image_copy = input_dir / f"source{source_image.suffix or '.jpg'}"
    audio_copy = input_dir / "reply.wav"
    shutil.copy2(source_image, image_copy)
    shutil.copy2(source_audio, audio_copy)

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    ffmpeg_dir = Path(args.ffmpeg_dir)
    if ffmpeg_dir.exists():
        env["PATH"] = str(ffmpeg_dir) + os.pathsep + env.get("PATH", "")

    python_exe = repo / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)

    command = [
        str(python_exe),
        "inference.py",
        "-s",
        str(image_copy),
        "-d",
        str(driving),
        "-o",
        str(raw_dir),
    ]
    if args.no_half:
        command.append("--flag-use-half-precision=False")

    run(command, repo, env)
    raw_video = newest_video(raw_dir)

    ffmpeg_exe = "ffmpeg"
    if ffmpeg_dir.exists() and (ffmpeg_dir / "ffmpeg.exe").exists():
        ffmpeg_exe = str(ffmpeg_dir / "ffmpeg.exe")

    mux_command = [
        ffmpeg_exe,
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(raw_video),
        "-i",
        str(audio_copy),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    run(mux_command, output_path.parent, env)
    print(f">> avatar video saved to: {output_path}", flush=True)


if __name__ == "__main__":
    main()
