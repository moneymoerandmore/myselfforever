# Avatar 3D Bridge

This service is the local adapter between the dashboard and the real 3D avatar
runtime.

It intentionally does not contain LivePortrait, MuseTalk, or any 2D generated
video pipeline. Its job is to provide a stable API for a persistent 3D character
process such as Audio2Face/ACE plus Unreal/MetaHuman.

## Start

```powershell
python services/avatar-3d-bridge/bridge.py --host 127.0.0.1 --port 8820
```

Optional Unreal command channel:

```powershell
python services/avatar-3d-bridge/bridge.py --host 127.0.0.1 --port 8820 --unreal-ws-url ws://127.0.0.1:8830/avatar
```

## API

- `GET /health`
- `GET /api/state`
- `GET /api/unreal/events?after=<event_id>&timeout=10`
- `POST /api/state`
- `POST /api/say`
- `POST /api/unreal/ack`

`/api/say` accepts relationship-graph text plus a streaming TTS URL. Until a
real 3D runtime adapter is attached, it returns `runtime_connected: false`.

The dashboard reads the visual stream URL from `runtime/avatar-runtime-3d/config.json`
or `AVATAR3D_STREAM_URL`; the bridge only coordinates state and commands.

## Recommended Unreal Integration

Start with HTTP pull. It avoids requiring Unreal to run a websocket server.

```text
Unreal -> GET http://127.0.0.1:8820/api/unreal/events?after=<last_event_id>&timeout=10
Unreal -> handle every returned event
Unreal -> POST http://127.0.0.1:8820/api/unreal/ack
```

The returned shape:

```json
{
  "ok": true,
  "result": {
    "events": [],
    "last_event_id": "",
    "state": {}
  }
}
```

Use `event.event_id` as the next `after` cursor. Events are kept in memory for
recent runtime control only; they are not a durable log.

## Unreal WebSocket Event Contract

When `UNREAL_WS_URL` or `AVATAR3D_UNREAL_WS_URL` is configured, the bridge also
sends one JSON websocket message per event. WebSocket push is optional; HTTP pull
is the baseline contract.

State event:

```json
{
  "type": "state",
  "sent_at": "2026-07-16T10:00:00",
  "provider": "nvidia_audio2face_unreal",
  "character_id": "digital_twin_3d",
  "payload": {
    "state": "thinking"
  }
}
```

Speech event:

```json
{
  "type": "say",
  "sent_at": "2026-07-16T10:00:00",
  "provider": "nvidia_audio2face_unreal",
  "character_id": "digital_twin_3d",
  "payload": {
    "id": "command-id",
    "text": "reply text",
    "audio_url": "/api/avatar3d/streaming-voice?text=...",
    "audio_chunks": [],
    "audio_format": "mp3",
    "voice_provider": "volcengine",
    "metadata": {
      "interaction_core": "relationship_graph_draft",
      "surface": "avatar_3d"
    }
  }
}
```

Unreal should map:

- `state=listening/thinking/speaking/idle/error` to animation state.
- `audio_url` or `audio_chunks` to an audio player / Audio2Face input.
- `text` and `metadata` to subtitles, logs, and debugging overlays only; the
  expression should be driven by audio, not by generated 2D video.
