#!/usr/bin/env python
"""Audio-driven lip-sync adapter using local Wav2Lip."""

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Path to the Wav2Lip repository.")
    parser.add_argument("--video", required=True, help="Input talking-head video.")
    parser.add_argument("--audio", required=True, help="Driving audio.")
    parser.add_argument("--out", required=True, help="Final lip-synced mp4 path.")
    parser.add_argument("--checkpoint", default="", help="Wav2Lip checkpoint. Defaults to checkpoints/wav2lip_gan.pth.")
    parser.add_argument("--ffmpeg-dir", default=DEFAULT_FFMPEG_DIR)
    parser.add_argument("--pads", nargs=4, default=["0", "15", "0", "0"])
    parser.add_argument("--face-det-batch-size", default="4")
    parser.add_argument("--wav2lip-batch-size", default="32")
    parser.add_argument("--resize-factor", default="1")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    source_video = Path(args.video).resolve()
    source_audio = Path(args.audio).resolve()
    output_path = Path(args.out).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not repo.exists():
        raise FileNotFoundError(f"Wav2Lip repo not found: {repo}")
    if not source_video.exists():
        raise FileNotFoundError(f"source video not found: {source_video}")
    if not source_audio.exists():
        raise FileNotFoundError(f"audio not found: {source_audio}")

    checkpoint = Path(args.checkpoint).resolve() if args.checkpoint else repo / "checkpoints" / "wav2lip_gan.pth"
    if not checkpoint.exists():
        raise FileNotFoundError(f"Wav2Lip checkpoint not found: {checkpoint}")

    work_dir = repo / "digital_twin_jobs" / f"{output_path.parent.name}-{uuid4().hex[:8]}"
    input_dir = work_dir / "input"
    output_dir = work_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    video_copy = input_dir / "base.mp4"
    audio_copy = input_dir / "reply.wav"
    wav2lip_output = output_dir / "avatar_lipsync.mp4"
    shutil.copy2(source_video, video_copy)
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
        "--checkpoint_path",
        str(checkpoint),
        "--face",
        str(video_copy),
        "--audio",
        str(audio_copy),
        "--outfile",
        str(wav2lip_output),
        "--pads",
        *[str(part) for part in args.pads],
        "--face_det_batch_size",
        str(args.face_det_batch_size),
        "--wav2lip_batch_size",
        str(args.wav2lip_batch_size),
        "--resize_factor",
        str(args.resize_factor),
    ]
    run(command, repo, env)
    if not wav2lip_output.exists():
        raise FileNotFoundError(f"Wav2Lip did not create output: {wav2lip_output}")

    shutil.copy2(wav2lip_output, output_path)
    print(f">> lip-synced avatar video saved to: {output_path}", flush=True)


if __name__ == "__main__":
    main()
