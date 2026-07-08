#!/usr/bin/env python
"""Persistent MuseTalk v1.5 HTTP worker for audio-driven lip sync."""

from __future__ import annotations

import argparse
import copy
import glob
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import pickle
import shutil
import subprocess
import sys
import threading
import time
import types
from typing import Any
from uuid import uuid4


DEFAULT_FFMPEG_DIR = (
    r"C:\Users\cloud\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1.2-full_build\bin"
)


coord_placeholder = (0.0, 0.0, 0.0, 0.0)


def install_lightweight_preprocessing() -> None:
    import cv2
    from tqdm import tqdm

    def read_imgs(img_list: list[str]) -> list[Any]:
        frames = []
        print("reading images...", flush=True)
        for img_path in tqdm(img_list):
            frames.append(cv2.imread(img_path))
        return frames

    def fallback_bbox(frame: Any) -> tuple[int, int, int, int]:
        h, w = frame.shape[:2]
        side = int(min(w, h) * 0.62)
        cx = w // 2
        x1 = max(0, cx - side // 2)
        x2 = min(w, cx + side // 2)
        y1 = max(0, int(h * 0.36))
        y2 = min(h, int(h * 0.86))
        return (x1, y1, x2, y2)

    def get_landmark_and_bbox(
        img_list: list[str],
        upperbondrange: int = 0,
    ) -> tuple[list[Any], list[Any]]:
        frames = read_imgs(img_list)
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        coords = []
        previous = None
        print("extracting lightweight face boxes...", flush=True)
        for frame in tqdm(frames):
            if frame is None:
                coords.append(previous or coord_placeholder)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=4,
                minSize=(80, 80),
            )
            if len(faces):
                x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
                x1 = max(0, int(x - 0.04 * w))
                x2 = min(frame.shape[1], int(x + 1.04 * w))
                y1 = max(0, int(y + 0.34 * h + upperbondrange))
                y2 = min(frame.shape[0], int(y + 1.05 * h))
                box = (x1, y1, x2, y2)
            else:
                box = previous or fallback_bbox(frame)
            previous = box
            coords.append(box)
        return coords, frames

    module = types.ModuleType("musetalk.utils.preprocessing")
    module.coord_placeholder = coord_placeholder
    module.read_imgs = read_imgs
    module.get_landmark_and_bbox = get_landmark_and_bbox
    sys.modules["musetalk.utils.preprocessing"] = module


def run_command(command: list[str], cwd: Path) -> None:
    print(">>", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=str(cwd))
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with exit code {completed.returncode}")


class MuseTalkWorker:
    def __init__(
        self,
        repo: Path,
        *,
        ffmpeg_dir: Path,
        batch_size: int = 4,
        use_float16: bool = True,
    ) -> None:
        self.repo = repo.resolve()
        self.ffmpeg_dir = ffmpeg_dir.resolve()
        self.batch_size = batch_size
        self.use_float16 = use_float16
        self.lock = threading.Lock()
        self.started_at = time.time()
        self.work_root = self.repo / "digital_twin_worker_jobs"
        self.realtime_root = self.repo / "digital_twin_realtime_avatars"
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.realtime_root.mkdir(parents=True, exist_ok=True)
        self.realtime_avatars: dict[str, dict[str, Any]] = {}

        if not self.repo.exists():
            raise FileNotFoundError(f"MuseTalk repo not found: {self.repo}")
        if str(self.repo) not in sys.path:
            sys.path.insert(0, str(self.repo))
        if self.ffmpeg_dir.exists():
            os.environ["PATH"] = str(self.ffmpeg_dir) + os.pathsep + os.environ.get("PATH", "")
        os.environ.setdefault("PYTHONUTF8", "1")
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        os.environ.setdefault("HF_HOME", str(self.repo / ".cache" / "hf"))
        os.environ.setdefault("TRANSFORMERS_CACHE", str(self.repo / ".cache" / "transformers"))
        install_lightweight_preprocessing()

        import torch
        from transformers import WhisperModel
        from musetalk.utils.audio_processor import AudioProcessor
        from musetalk.utils.face_parsing import FaceParsing
        from musetalk.utils.utils import load_all_model

        self.torch = torch
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        load_started = time.time()
        self.vae, self.unet, self.pe = load_all_model(
            unet_model_path=str(self.repo / "models" / "musetalkV15" / "unet.pth"),
            vae_type="sd-vae",
            unet_config=str(self.repo / "models" / "musetalkV15" / "musetalk.json"),
            device=self.device,
        )
        if self.use_float16:
            self.pe = self.pe.half()
            self.vae.vae = self.vae.vae.half()
            self.unet.model = self.unet.model.half()
        self.pe = self.pe.to(self.device)
        self.vae.vae = self.vae.vae.to(self.device)
        self.unet.model = self.unet.model.to(self.device)
        self.timesteps = torch.tensor([0], device=self.device)
        self.audio_processor = AudioProcessor(feature_extractor_path=str(self.repo / "models" / "whisper"))
        self.weight_dtype = self.unet.model.dtype
        self.whisper = WhisperModel.from_pretrained(str(self.repo / "models" / "whisper"))
        self.whisper = self.whisper.to(device=self.device, dtype=self.weight_dtype).eval()
        self.whisper.requires_grad_(False)
        self.face_parser = FaceParsing(left_cheek_width=90, right_cheek_width=90)
        self.load_seconds = round(time.time() - load_started, 2)

    def _video_to_images(self, video_path: Path, output_dir: Path) -> list[str]:
        import cv2

        output_dir.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(str(video_path))
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            cv2.imwrite(str(output_dir / f"{index:08d}.png"), frame)
            index += 1
        cap.release()
        if index == 0:
            raise RuntimeError(f"no frames extracted from {video_path}")
        return sorted(glob.glob(str(output_dir / "*.[jpJP][pnPN]*[gG]")))

    def prepare_realtime_avatar(
        self,
        avatar_id: str,
        video_path: Path,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        import cv2
        from tqdm import tqdm
        from musetalk.utils.blending import get_image_prepare_material
        from musetalk.utils.preprocessing import get_landmark_and_bbox, read_imgs

        safe_avatar_id = "".join(ch if ch.isalnum() or ch in "_.-" else "_" for ch in avatar_id)
        avatar_dir = self.realtime_root / safe_avatar_id
        source_dir = avatar_dir / "source"
        full_imgs_dir = avatar_dir / "full_imgs"
        mask_dir = avatar_dir / "mask"
        latents_path = avatar_dir / "latents.pt"
        coords_path = avatar_dir / "coords.pkl"
        mask_coords_path = avatar_dir / "mask_coords.pkl"
        info_path = avatar_dir / "avatar_info.json"

        if (
            not force
            and latents_path.exists()
            and coords_path.exists()
            and mask_coords_path.exists()
            and full_imgs_dir.exists()
            and mask_dir.exists()
        ):
            return self.load_realtime_avatar(safe_avatar_id)

        if not video_path.exists():
            raise FileNotFoundError(f"realtime avatar video not found: {video_path}")

        if avatar_dir.exists() and force:
            shutil.rmtree(avatar_dir)
        source_dir.mkdir(parents=True, exist_ok=True)
        full_imgs_dir.mkdir(parents=True, exist_ok=True)
        mask_dir.mkdir(parents=True, exist_ok=True)
        source_video = source_dir / "base.mp4"
        shutil.copy2(video_path, source_video)

        started = time.time()
        input_img_list = self._video_to_images(source_video, full_imgs_dir)
        coord_list, frame_list = get_landmark_and_bbox(input_img_list, 0)
        input_latent_list = []
        for index, (bbox, frame) in enumerate(zip(coord_list, frame_list)):
            if bbox == coord_placeholder:
                continue
            x1, y1, x2, y2 = bbox
            y2 = min(y2 + 10, frame.shape[0])
            coord_list[index] = [x1, y1, x2, y2]
            crop_frame = frame[y1:y2, x1:x2]
            crop_frame = cv2.resize(crop_frame, (256, 256), interpolation=cv2.INTER_LANCZOS4)
            input_latent_list.append(self.vae.get_latents_for_unet(crop_frame))
        if not input_latent_list:
            raise RuntimeError("no valid realtime avatar latents were extracted")

        frame_list_cycle = frame_list + frame_list[::-1]
        coord_list_cycle = coord_list + coord_list[::-1]
        input_latent_list_cycle = input_latent_list + input_latent_list[::-1]
        mask_coords_list_cycle = []
        mask_list_cycle = []

        shutil.rmtree(full_imgs_dir, ignore_errors=True)
        shutil.rmtree(mask_dir, ignore_errors=True)
        full_imgs_dir.mkdir(parents=True, exist_ok=True)
        mask_dir.mkdir(parents=True, exist_ok=True)
        for index, frame in enumerate(tqdm(frame_list_cycle)):
            cv2.imwrite(str(full_imgs_dir / f"{index:08d}.png"), frame)
            x1, y1, x2, y2 = coord_list_cycle[index]
            mask, crop_box = get_image_prepare_material(
                frame,
                [x1, y1, x2, y2],
                fp=self.face_parser,
                mode="jaw",
            )
            cv2.imwrite(str(mask_dir / f"{index:08d}.png"), mask)
            mask_coords_list_cycle.append(crop_box)
            mask_list_cycle.append(mask)

        with coords_path.open("wb") as handle:
            pickle.dump(coord_list_cycle, handle)
        with mask_coords_path.open("wb") as handle:
            pickle.dump(mask_coords_list_cycle, handle)
        self.torch.save(input_latent_list_cycle, str(latents_path))
        info_path.write_text(
            json.dumps(
                {
                    "avatar_id": safe_avatar_id,
                    "video_path": str(source_video),
                    "source_video": str(video_path),
                    "frame_count": len(frame_list_cycle),
                    "prepared_at": time.time(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        avatar = self.load_realtime_avatar(safe_avatar_id)
        avatar["prepare_seconds"] = round(time.time() - started, 2)
        return avatar

    def load_realtime_avatar(self, avatar_id: str) -> dict[str, Any]:
        from musetalk.utils.preprocessing import read_imgs

        safe_avatar_id = "".join(ch if ch.isalnum() or ch in "_.-" else "_" for ch in avatar_id)
        avatar_dir = self.realtime_root / safe_avatar_id
        full_imgs_dir = avatar_dir / "full_imgs"
        mask_dir = avatar_dir / "mask"
        latents_path = avatar_dir / "latents.pt"
        coords_path = avatar_dir / "coords.pkl"
        mask_coords_path = avatar_dir / "mask_coords.pkl"
        if safe_avatar_id in self.realtime_avatars:
            return self.realtime_avatars[safe_avatar_id]["meta"]
        if not latents_path.exists():
            raise FileNotFoundError(f"realtime avatar is not prepared: {safe_avatar_id}")
        input_img_list = sorted(glob.glob(str(full_imgs_dir / "*.[jpJP][pnPN]*[gG]")))
        mask_img_list = sorted(glob.glob(str(mask_dir / "*.[jpJP][pnPN]*[gG]")))
        with coords_path.open("rb") as handle:
            coord_list_cycle = pickle.load(handle)
        with mask_coords_path.open("rb") as handle:
            mask_coords_list_cycle = pickle.load(handle)
        avatar = {
            "latents": self.torch.load(str(latents_path), map_location=self.device),
            "coords": coord_list_cycle,
            "frames": read_imgs(input_img_list),
            "mask_coords": mask_coords_list_cycle,
            "masks": read_imgs(mask_img_list),
        }
        meta = {
            "avatar_id": safe_avatar_id,
            "avatar_path": str(avatar_dir),
            "frame_count": len(avatar["frames"]),
            "latent_count": len(avatar["latents"]),
            "loaded": True,
        }
        self.realtime_avatars[safe_avatar_id] = {"data": avatar, "meta": meta}
        return meta

    def realtime_lipsync(
        self,
        avatar_id: str,
        audio_path: Path,
        output_path: Path,
        *,
        video_path: Path | None = None,
        batch_size: int | None = None,
        fps: int = 25,
    ) -> dict[str, Any]:
        import cv2
        import numpy as np
        from tqdm import tqdm
        from musetalk.utils.blending import get_image_blending
        from musetalk.utils.utils import datagen

        if video_path and video_path.exists():
            self.prepare_realtime_avatar(avatar_id, video_path, force=False)
        else:
            self.load_realtime_avatar(avatar_id)
        if not audio_path.exists():
            raise FileNotFoundError(f"audio not found: {audio_path}")

        safe_avatar_id = "".join(ch if ch.isalnum() or ch in "_.-" else "_" for ch in avatar_id)
        avatar_pack = self.realtime_avatars[safe_avatar_id]
        avatar = avatar_pack["data"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        work_dir = self.work_root / f"realtime-{output_path.parent.name}-{uuid4().hex[:8]}"
        frame_dir = work_dir / "frames"
        frame_dir.mkdir(parents=True, exist_ok=True)
        temp_video = work_dir / "temp.mp4"

        started = time.time()
        with self.lock:
            whisper_input_features, librosa_length = self.audio_processor.get_audio_feature(
                str(audio_path),
                weight_dtype=self.weight_dtype,
            )
            whisper_chunks = self.audio_processor.get_whisper_chunk(
                whisper_input_features,
                self.device,
                self.weight_dtype,
                self.whisper,
                librosa_length,
                fps=fps,
                audio_padding_length_left=2,
                audio_padding_length_right=2,
            )
            gen = datagen(
                whisper_chunks,
                avatar["latents"],
                batch_size or self.batch_size,
            )
            frame_index = 0
            total = int(np.ceil(float(len(whisper_chunks)) / (batch_size or self.batch_size)))
            with self.torch.no_grad():
                for whisper_batch, latent_batch in tqdm(gen, total=total):
                    audio_feature_batch = self.pe(whisper_batch.to(self.device))
                    latent_batch = latent_batch.to(device=self.device, dtype=self.unet.model.dtype)
                    pred_latents = self.unet.model(
                        latent_batch,
                        self.timesteps,
                        encoder_hidden_states=audio_feature_batch,
                    ).sample
                    pred_latents = pred_latents.to(device=self.device, dtype=self.vae.vae.dtype)
                    recon = self.vae.decode_latents(pred_latents)
                    for res_frame in recon:
                        bbox = avatar["coords"][frame_index % len(avatar["coords"])]
                        if bbox == coord_placeholder:
                            continue
                        ori_frame = copy.deepcopy(avatar["frames"][frame_index % len(avatar["frames"])])
                        x1, y1, x2, y2 = bbox
                        try:
                            res_frame = cv2.resize(res_frame.astype(np.uint8), (x2 - x1, y2 - y1))
                        except Exception:
                            continue
                        mask = avatar["masks"][frame_index % len(avatar["masks"])]
                        mask_crop_box = avatar["mask_coords"][frame_index % len(avatar["mask_coords"])]
                        combine_frame = get_image_blending(ori_frame, res_frame, bbox, mask, mask_crop_box)
                        cv2.imwrite(str(frame_dir / f"{frame_index:08d}.png"), combine_frame)
                        frame_index += 1

            run_command(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "warning",
                    "-r",
                    str(fps),
                    "-f",
                    "image2",
                    "-i",
                    str(frame_dir / "%08d.png"),
                    "-vcodec",
                    "libx264",
                    "-vf",
                    "format=yuv420p",
                    "-crf",
                    "18",
                    str(temp_video),
                ],
                self.repo,
            )
            run_command(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "warning",
                    "-i",
                    str(audio_path),
                    "-i",
                    str(temp_video),
                    str(output_path),
                ],
                self.repo,
            )

        return {
            "video_path": str(output_path),
            "avatar_id": safe_avatar_id,
            "frame_count": frame_index,
            "inference_seconds": round(time.time() - started, 2),
            "model_load_seconds": self.load_seconds,
            "realtime_avatar": avatar_pack["meta"],
            "work_dir": str(work_dir),
        }

    def lipsync(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        *,
        batch_size: int | None = None,
    ) -> dict[str, Any]:
        if not video_path.exists():
            raise FileNotFoundError(f"source video not found: {video_path}")
        if not audio_path.exists():
            raise FileNotFoundError(f"audio not found: {audio_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        work_dir = self.work_root / f"{output_path.parent.name}-{uuid4().hex[:8]}"
        input_dir = work_dir / "input"
        result_dir = work_dir / "results" / "v15"
        input_dir.mkdir(parents=True, exist_ok=True)
        result_dir.mkdir(parents=True, exist_ok=True)
        video_copy = input_dir / "base.mp4"
        audio_copy = input_dir / "reply.wav"
        shutil.copy2(video_path, video_copy)
        shutil.copy2(audio_path, audio_copy)
        worker_output = result_dir / "avatar_musetalk.mp4"

        started = time.time()
        with self.lock:
            self._run_lipsync(video_copy, audio_copy, worker_output, batch_size or self.batch_size)
        if not worker_output.exists():
            raise FileNotFoundError(f"MuseTalk did not create output: {worker_output}")
        shutil.copy2(worker_output, output_path)
        return {
            "video_path": str(output_path),
            "inference_seconds": round(time.time() - started, 2),
            "model_load_seconds": self.load_seconds,
            "uptime_seconds": round(time.time() - self.started_at, 2),
            "work_dir": str(work_dir),
        }

    def _run_lipsync(self, video_path: Path, audio_path: Path, output_vid_name: Path, batch_size: int) -> None:
        import cv2
        import math
        import numpy as np
        from tqdm import tqdm
        from musetalk.utils.blending import get_image
        from musetalk.utils.utils import datagen, get_file_type, get_video_fps
        from musetalk.utils.preprocessing import get_landmark_and_bbox, read_imgs

        torch = self.torch
        temp_dir = output_vid_name.parent
        input_basename = video_path.stem
        audio_basename = audio_path.stem
        output_basename = f"{input_basename}_{audio_basename}"
        result_img_save_path = temp_dir / output_basename
        result_img_save_path.mkdir(parents=True, exist_ok=True)
        crop_coord_save_path = output_vid_name.parent.parent / f"{input_basename}.pkl"

        save_dir_full: Path | None = None
        file_type = get_file_type(str(video_path))
        if file_type == "video":
            save_dir_full = temp_dir / input_basename
            save_dir_full.mkdir(parents=True, exist_ok=True)
            run_command(
                [
                    "ffmpeg",
                    "-v",
                    "fatal",
                    "-i",
                    str(video_path),
                    "-start_number",
                    "0",
                    str(save_dir_full / "%08d.png"),
                ],
                self.repo,
            )
            input_img_list = sorted(
                glob.glob(str(save_dir_full / "*.[jpJP][pnPN]*[gG]"))
            )
            fps = get_video_fps(str(video_path))
        elif file_type == "image":
            input_img_list = [str(video_path)]
            fps = 25
        elif video_path.is_dir():
            input_img_list = sorted(glob.glob(str(video_path / "*.[jpJP][pnPN]*[gG]")))
            fps = 25
        else:
            raise ValueError(f"{video_path} should be a video file, image file, or image directory")

        whisper_input_features, librosa_length = self.audio_processor.get_audio_feature(str(audio_path))
        whisper_chunks = self.audio_processor.get_whisper_chunk(
            whisper_input_features,
            self.device,
            self.weight_dtype,
            self.whisper,
            librosa_length,
            fps=fps,
            audio_padding_length_left=2,
            audio_padding_length_right=2,
        )

        if crop_coord_save_path.exists():
            with crop_coord_save_path.open("rb") as handle:
                coord_list = pickle.load(handle)
            frame_list = read_imgs(input_img_list)
        else:
            coord_list, frame_list = get_landmark_and_bbox(input_img_list, 0)
            with crop_coord_save_path.open("wb") as handle:
                pickle.dump(coord_list, handle)

        input_latent_list = []
        for bbox, frame in zip(coord_list, frame_list):
            if bbox == coord_placeholder:
                continue
            x1, y1, x2, y2 = bbox
            y2 = min(y2 + 10, frame.shape[0])
            crop_frame = frame[y1:y2, x1:x2]
            crop_frame = cv2.resize(crop_frame, (256, 256), interpolation=cv2.INTER_LANCZOS4)
            input_latent_list.append(self.vae.get_latents_for_unet(crop_frame))

        if not input_latent_list:
            raise RuntimeError("no valid face latents were extracted")

        frame_list_cycle = frame_list + frame_list[::-1]
        coord_list_cycle = coord_list + coord_list[::-1]
        input_latent_list_cycle = input_latent_list + input_latent_list[::-1]

        video_num = len(whisper_chunks)
        gen = datagen(
            whisper_chunks=whisper_chunks,
            vae_encode_latents=input_latent_list_cycle,
            batch_size=batch_size,
            delay_frame=0,
            device=self.device,
        )
        res_frame_list = []
        total = int(np.ceil(float(video_num) / batch_size))
        with torch.no_grad():
            for whisper_batch, latent_batch in tqdm(gen, total=total):
                audio_feature_batch = self.pe(whisper_batch)
                latent_batch = latent_batch.to(dtype=self.unet.model.dtype)
                pred_latents = self.unet.model(
                    latent_batch,
                    self.timesteps,
                    encoder_hidden_states=audio_feature_batch,
                ).sample
                res_frame_list.extend(self.vae.decode_latents(pred_latents))

        for i, res_frame in enumerate(tqdm(res_frame_list)):
            bbox = coord_list_cycle[i % len(coord_list_cycle)]
            if bbox == coord_placeholder:
                continue
            ori_frame = copy.deepcopy(frame_list_cycle[i % len(frame_list_cycle)])
            x1, y1, x2, y2 = bbox
            y2 = min(y2 + 10, ori_frame.shape[0])
            try:
                res_frame = cv2.resize(res_frame.astype(np.uint8), (x2 - x1, y2 - y1))
            except Exception:
                continue
            combine_frame = get_image(
                ori_frame,
                res_frame,
                [x1, y1, x2, y2],
                mode="jaw",
                fp=self.face_parser,
            )
            cv2.imwrite(str(result_img_save_path / f"{i:08d}.png"), combine_frame)

        temp_vid_path = temp_dir / f"temp_{input_basename}_{audio_basename}.mp4"
        run_command(
            [
                "ffmpeg",
                "-y",
                "-v",
                "warning",
                "-r",
                str(fps),
                "-f",
                "image2",
                "-i",
                str(result_img_save_path / "%08d.png"),
                "-vcodec",
                "libx264",
                "-vf",
                "format=yuv420p",
                "-crf",
                "18",
                str(temp_vid_path),
            ],
            self.repo,
        )
        run_command(
            [
                "ffmpeg",
                "-y",
                "-v",
                "warning",
                "-i",
                str(audio_path),
                "-i",
                str(temp_vid_path),
                str(output_vid_name),
            ],
            self.repo,
        )

        shutil.rmtree(result_img_save_path, ignore_errors=True)
        if temp_vid_path.exists():
            temp_vid_path.unlink()
        if save_dir_full:
            shutil.rmtree(save_dir_full, ignore_errors=True)


class WorkerHandler(BaseHTTPRequestHandler):
    server_version = "MuseTalkWorker/0.1"
    worker: MuseTalkWorker

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_json(
            {
                "ok": True,
                "provider": "musetalk",
                "model_loaded": True,
                "model_load_seconds": self.worker.load_seconds,
                "realtime_avatar_count": len(self.worker.realtime_avatars),
                "uptime_seconds": round(time.time() - self.worker.started_at, 2),
            }
        )

    def do_POST(self) -> None:
        if self.path not in {"/lipsync", "/prepare-realtime-avatar", "/realtime-lipsync"}:
            self.send_error(404)
            return
        try:
            payload = self.read_json()
            if self.path == "/prepare-realtime-avatar":
                result = self.worker.prepare_realtime_avatar(
                    str(payload.get("avatar_id") or "digital_twin"),
                    Path(str(payload.get("video_path") or "")).resolve(),
                    force=bool(payload.get("force", False)),
                )
            elif self.path == "/realtime-lipsync":
                video_value = str(payload.get("video_path") or "").strip()
                result = self.worker.realtime_lipsync(
                    str(payload.get("avatar_id") or "digital_twin"),
                    Path(str(payload.get("audio_path") or "")).resolve(),
                    Path(str(payload.get("output_path") or "")).resolve(),
                    video_path=Path(video_value).resolve() if video_value else None,
                    batch_size=int(payload.get("batch_size") or self.worker.batch_size),
                    fps=int(payload.get("fps") or 25),
                )
            else:
                result = self.worker.lipsync(
                    Path(str(payload.get("video_path") or "")).resolve(),
                    Path(str(payload.get("audio_path") or "")).resolve(),
                    Path(str(payload.get("output_path") or "")).resolve(),
                    batch_size=int(payload.get("batch_size") or self.worker.batch_size),
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
    parser = argparse.ArgumentParser(description="Run persistent MuseTalk worker.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8812)
    parser.add_argument("--ffmpeg-dir", default=DEFAULT_FFMPEG_DIR)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--no-float16", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    WorkerHandler.worker = MuseTalkWorker(
        Path(args.repo),
        ffmpeg_dir=Path(args.ffmpeg_dir),
        batch_size=args.batch_size,
        use_float16=not args.no_float16,
    )
    server = ThreadingHTTPServer((args.host, args.port), WorkerHandler)
    print(f"MuseTalk worker listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping MuseTalk worker.", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
