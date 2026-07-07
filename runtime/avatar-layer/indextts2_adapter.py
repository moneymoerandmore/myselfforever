#!/usr/bin/env python
"""IndexTTS2 adapter for the avatar layer.

This script is intentionally thin: it expects to run inside the IndexTTS2
environment and only translates the dashboard contract into IndexTTS2 calls.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate reply.wav with IndexTTS2.")
    parser.add_argument("--text", required=True, help="UTF-8 text file to synthesize.")
    parser.add_argument("--out", required=True, help="Output wav path.")
    parser.add_argument("--voice", required=True, help="Speaker reference wav path.")
    parser.add_argument("--repo", default=".", help="IndexTTS2 repository root.")
    parser.add_argument("--emotion-audio", default="", help="Optional emotion reference wav.")
    parser.add_argument("--emotion-text", default="", help="Optional text emotion description.")
    parser.add_argument("--emotion-alpha", type=float, default=0.6)
    parser.add_argument("--fp16", action="store_true", help="Use FP16 inference.")
    parser.add_argument("--cuda-kernel", action="store_true", help="Use IndexTTS CUDA kernel.")
    parser.add_argument("--deepspeed", action="store_true", help="Use DeepSpeed.")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    text_path = Path(args.text).resolve()
    output_path = Path(args.out).resolve()
    voice_path = Path(args.voice).resolve()
    cfg_path = repo / "checkpoints" / "config.yaml"
    model_dir = repo / "checkpoints"

    if not repo.exists():
        raise SystemExit(f"IndexTTS repo not found: {repo}")
    if not cfg_path.exists():
        raise SystemExit(f"IndexTTS config not found: {cfg_path}")
    if not voice_path.exists():
        raise SystemExit(f"speaker reference audio not found: {voice_path}")

    sys.path.insert(0, str(repo))
    from indextts.infer_v2 import IndexTTS2  # type: ignore

    text = text_path.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit("input text is empty")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tts = IndexTTS2(
        cfg_path=str(cfg_path),
        model_dir=str(model_dir),
        use_fp16=args.fp16,
        use_cuda_kernel=args.cuda_kernel,
        use_deepspeed=args.deepspeed,
    )

    kwargs = {
        "spk_audio_prompt": str(voice_path),
        "text": text,
        "output_path": str(output_path),
        "verbose": args.verbose,
    }
    if args.emotion_audio:
        kwargs["emo_audio_prompt"] = str(Path(args.emotion_audio).resolve())
        kwargs["emo_alpha"] = args.emotion_alpha
    elif args.emotion_text:
        kwargs["use_emo_text"] = True
        kwargs["emo_text"] = args.emotion_text
        kwargs["emo_alpha"] = args.emotion_alpha

    tts.infer(**kwargs)
    if not output_path.exists():
        raise SystemExit(f"IndexTTS2 did not create output wav: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
