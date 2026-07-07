#!/usr/bin/env python
"""Audio-driven lip-sync adapter using local MuseTalk v1.5."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
from uuid import uuid4


DEFAULT_FFMPEG_DIR = (
    r"C:\Users\cloud\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1.2-full_build\bin"
)


RUNNER = r'''
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import types

import cv2
import numpy as np
from tqdm import tqdm


coord_placeholder = (0.0, 0.0, 0.0, 0.0)


def read_imgs(img_list):
    frames = []
    print("reading images...")
    for img_path in tqdm(img_list):
        frames.append(cv2.imread(img_path))
    return frames


def _fallback_bbox(frame):
    h, w = frame.shape[:2]
    side = int(min(w, h) * 0.62)
    cx = w // 2
    x1 = max(0, cx - side // 2)
    x2 = min(w, cx + side // 2)
    y1 = max(0, int(h * 0.36))
    y2 = min(h, int(h * 0.86))
    return (x1, y1, x2, y2)


def get_landmark_and_bbox(img_list, upperbondrange=0):
    frames = read_imgs(img_list)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    coords = []
    previous = None
    print("extracting lightweight face boxes...")
    for frame in tqdm(frames):
        if frame is None:
            coords.append(previous or coord_placeholder)
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(80, 80))
        if len(faces):
            x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
            x1 = max(0, int(x - 0.04 * w))
            x2 = min(frame.shape[1], int(x + 1.04 * w))
            y1 = max(0, int(y + 0.34 * h + upperbondrange))
            y2 = min(frame.shape[0], int(y + 1.05 * h))
            box = (x1, y1, x2, y2)
        else:
            box = previous or _fallback_bbox(frame)
        previous = box
        coords.append(box)
    return coords, frames


def install_preprocessing_stub():
    module = types.ModuleType("musetalk.utils.preprocessing")
    module.coord_placeholder = coord_placeholder
    module.read_imgs = read_imgs
    module.get_landmark_and_bbox = get_landmark_and_bbox
    sys.modules["musetalk.utils.preprocessing"] = module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--output-name", required=True)
    parser.add_argument("--ffmpeg-dir", required=True)
    parser.add_argument("--batch-size", default="4")
    parser.add_argument("--no-float16", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    sys.path.insert(0, str(repo))
    install_preprocessing_stub()

    from scripts.inference import main as inference_main

    inference_args = argparse.Namespace(
        ffmpeg_path=args.ffmpeg_dir,
        gpu_id=0,
        vae_type="sd-vae",
        unet_config=str(repo / "models" / "musetalkV15" / "musetalk.json"),
        unet_model_path=str(repo / "models" / "musetalkV15" / "unet.pth"),
        whisper_dir=str(repo / "models" / "whisper"),
        inference_config=args.config,
        bbox_shift=0,
        result_dir=args.result_dir,
        extra_margin=10,
        fps=25,
        audio_padding_length_left=2,
        audio_padding_length_right=2,
        batch_size=int(args.batch_size),
        output_vid_name=args.output_name,
        use_saved_coord=False,
        saved_coord=False,
        use_float16=not args.no_float16,
        parsing_mode="jaw",
        left_cheek_width=90,
        right_cheek_width=90,
        version="v15",
    )
    inference_main(inference_args)


if __name__ == "__main__":
    main()
'''


def run(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    print(">>", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=str(cwd), env=env)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with exit code {completed.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Path to the MuseTalk repository.")
    parser.add_argument("--video", required=True, help="Input talking-head video.")
    parser.add_argument("--audio", required=True, help="Driving audio.")
    parser.add_argument("--out", required=True, help="Final lip-synced mp4 path.")
    parser.add_argument("--ffmpeg-dir", default=DEFAULT_FFMPEG_DIR)
    parser.add_argument("--batch-size", default="4")
    parser.add_argument("--no-float16", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    source_video = Path(args.video).resolve()
    source_audio = Path(args.audio).resolve()
    output_path = Path(args.out).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not repo.exists():
        raise FileNotFoundError(f"MuseTalk repo not found: {repo}")
    if not source_video.exists():
        raise FileNotFoundError(f"source video not found: {source_video}")
    if not source_audio.exists():
        raise FileNotFoundError(f"audio not found: {source_audio}")

    work_dir = repo / "digital_twin_jobs" / f"{output_path.parent.name}-{uuid4().hex[:8]}"
    input_dir = work_dir / "input"
    result_dir = work_dir / "results"
    input_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    video_copy = input_dir / "base.mp4"
    audio_copy = input_dir / "reply.wav"
    config_path = work_dir / "inference.yaml"
    runner_path = work_dir / "runner.py"
    output_name = "avatar_musetalk.mp4"
    musetalk_output = result_dir / "v15" / output_name

    shutil.copy2(source_video, video_copy)
    shutil.copy2(source_audio, audio_copy)
    config_path.write_text(
        "task_0:\n"
        f"  video_path: \"{video_copy.as_posix()}\"\n"
        f"  audio_path: \"{audio_copy.as_posix()}\"\n"
        f"  result_name: \"{output_name}\"\n",
        encoding="utf-8",
    )
    runner_path.write_text(textwrap.dedent(RUNNER), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["HF_HOME"] = str(repo / ".cache" / "hf")
    env["TRANSFORMERS_CACHE"] = str(repo / ".cache" / "transformers")
    ffmpeg_dir = Path(args.ffmpeg_dir)
    if ffmpeg_dir.exists():
        env["PATH"] = str(ffmpeg_dir) + os.pathsep + env.get("PATH", "")

    python_exe = repo / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)

    command = [
        str(python_exe),
        str(runner_path),
        "--repo",
        str(repo),
        "--config",
        str(config_path),
        "--result-dir",
        str(result_dir),
        "--output-name",
        output_name,
        "--ffmpeg-dir",
        str(ffmpeg_dir),
        "--batch-size",
        str(args.batch_size),
    ]
    if args.no_float16:
        command.append("--no-float16")

    run(command, repo, env)
    if not musetalk_output.exists():
        raise FileNotFoundError(f"MuseTalk did not create output: {musetalk_output}")

    shutil.copy2(musetalk_output, output_path)
    print(f">> MuseTalk lip-synced avatar video saved to: {output_path}", flush=True)


if __name__ == "__main__":
    main()
