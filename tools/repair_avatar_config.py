from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    config_path = ROOT / "runtime" / "avatar-layer" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    config["source_image_path"] = str(ROOT / "runtime" / "avatar-layer" / "portrait.jpg")
    config["base_video_path"] = str(ROOT / "runtime" / "avatar-layer" / "cache" / "base_idle.mp4")
    config["tts_command"] = (
        "cd /d D:\\AI\\index-tts && C:\\Users\\cloud\\.local\\bin\\uv.exe run python "
        + str(ROOT / "runtime" / "avatar-layer" / "indextts2_adapter.py")
        + " --repo D:\\AI\\index-tts --voice "
        + str(ROOT / "runtime" / "avatar-layer" / "voice_ref.wav")
        + " --text {text_path} --out {audio_path} --fp16"
    )
    config["liveportrait_command"] = (
        "C:\\Users\\cloud\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe "
        + str(ROOT / "runtime" / "avatar-layer" / "liveportrait_adapter.py")
        + " --repo D:\\AI\\LivePortrait --image {image_path} --audio {audio_path} --out {output_path}"
    )
    config["lipsync_command"] = (
        "C:\\Users\\cloud\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe "
        + str(ROOT / "runtime" / "avatar-layer" / "musetalk_adapter.py")
        + " --repo D:\\AI\\MuseTalk --video {video_path} --audio {audio_path} --out {output_path} --batch-size 2"
    )
    config["lipsync_fps"] = "16"
    config["lipsync_batch_size"] = "4"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print("avatar config repaired")


if __name__ == "__main__":
    main()
