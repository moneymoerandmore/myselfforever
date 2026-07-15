from __future__ import annotations

import json
from pathlib import Path
import time
import urllib.request


BASE_URL = "http://127.0.0.1:8788"
STREAM_URL = "http://127.0.0.1:8813"


def read_json(url: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    payload = {
        "draft_text": "\u8fd9\u7248\u6d4b\u8bd5\u540c\u6b65\u53e3\u578b\u3002",
        "query": "latency-test",
        "scenario": "local sync test",
        "relationship_graph_surface": True,
        "multimodal_output_surface": "avatar",
        "latency_profile": "fast_avatar",
        "streaming": True,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        BASE_URL + "/api/avatar/realtime-reply",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    reply_seconds = time.perf_counter() - started
    result = data["result"]
    voice = result.get("clone_voice") or {}
    visual = voice.get("visual_driver") or {}
    chunks = voice.get("audio_chunks") or []
    print(
        json.dumps(
            {
                "reply_seconds": round(reply_seconds, 3),
                "draft_text": result.get("draft_text"),
                "chunk_count": len(chunks),
                "visual_enabled": visual.get("enabled"),
                "sync_mode": visual.get("sync_mode"),
                "sessions": visual.get("sessions"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    audio_timings = []
    for chunk in chunks:
        url = BASE_URL + chunk["audio_url"]
        audio_started = time.perf_counter()
        with urllib.request.urlopen(url, timeout=20) as response:
            audio_bytes = response.read()
            transport = response.headers.get("X-Voice-Transport")
            content_type = response.headers.get("Content-Type")
        audio_timings.append(
            {
                "index": chunk.get("index"),
                "text": chunk.get("text"),
                "session_id": chunk.get("visual_session_id"),
                "seconds": round(time.perf_counter() - audio_started, 3),
                "bytes": len(audio_bytes),
                "transport": transport,
                "content_type": content_type,
            }
        )
    print(json.dumps({"audio_timings": audio_timings}, ensure_ascii=False, indent=2))

    session_ids = [chunk.get("visual_session_id") for chunk in chunks if chunk.get("visual_session_id")]
    seen: dict[str, dict] = {}
    poll_started = time.perf_counter()
    deadline = poll_started + 45
    while time.perf_counter() < deadline:
        done = True
        for session_id in session_ids:
            try:
                status = read_json(f"{STREAM_URL}/sync-status?session_id={session_id}", timeout=2)
            except Exception as exc:
                status = {"ok": False, "error": str(exc), "session_id": session_id}
            seen[session_id] = status
            if not status.get("ok") or (status.get("frame_count") or 0) < 1:
                done = False
        if done:
            break
        time.sleep(0.5)
    print(
        json.dumps(
            {"sync_status": seen, "poll_seconds": round(time.perf_counter() - poll_started, 3)},
            ensure_ascii=False,
            indent=2,
        )
    )

    cache_dir = Path("data/generated/avatar-layer/_realtime-audio-cache")
    files = sorted(cache_dir.glob("*.mp3"), key=lambda path: path.stat().st_mtime, reverse=True)[:5]
    print(
        json.dumps(
            {"recent_audio_cache": [{"name": path.name, "bytes": path.stat().st_size} for path in files]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
