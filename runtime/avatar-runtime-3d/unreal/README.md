# Unreal Runtime Integration

This folder contains the first Unreal-side contract for the persistent 3D avatar.

Start with HTTP pull because it works with Unreal's built-in HTTP module and does
not require a websocket server inside Unreal.

## Bridge Endpoints

```text
GET  http://127.0.0.1:8820/api/unreal/events?after=<last_event_id>&timeout=10
POST http://127.0.0.1:8820/api/unreal/ack
```

## Event Types

`state`:

```json
{
  "event_id": "cursor",
  "type": "state",
  "payload": {
    "state": "thinking"
  }
}
```

`say`:

```json
{
  "event_id": "cursor",
  "type": "say",
  "payload": {
    "text": "reply text",
    "audio_url": "/api/avatar3d/streaming-voice?text=...",
    "audio_chunks": [],
    "audio_format": "mp3",
    "voice_provider": "volcengine",
    "character_id": "digital_twin_3d"
  }
}
```

## Unreal Mapping

1. Add an actor component like `AvatarRuntimeHttpClient`.
2. Set `BridgeBaseUrl` to `http://127.0.0.1:8820`.
3. Bind `OnAvatarState` to animation state changes.
4. Bind `OnAvatarSay` to audio playback and Audio2Face input.
5. Render the character through Unreal Pixel Streaming or another WebRTC surface,
   then set `stream_url` in `runtime/avatar-runtime-3d/config.local.json`.

The bridge should remain the only boundary between the relationship-graph
interaction core and the 3D renderer. Unreal must not generate persona text; it
only receives expression/runtime commands.
