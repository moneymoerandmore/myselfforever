# Avatar Runtime 3D

This is the active avatar route for the external interaction layer.

The old 2D path based on still portraits, LivePortrait, MuseTalk, generated videos,
MJPEG idle streams, and canvas mouth overlays is deprecated for the main product
surface. The dashboard page `/avatar.html` now talks to a persistent 3D runtime
contract instead.

## Runtime Shape

- Interaction core: relationship graph draft generation.
- Voice: existing streaming clone TTS, currently configured through the avatar voice settings.
- Face/body: persistent 3D runtime, expected to be Audio2Face/ACE plus Unreal/MetaHuman or an equivalent local 3D stack.
- Transport: WebRTC or Pixel Streaming for the visual stream.
- Bridge: `services/avatar-3d-bridge` exposes a local API that the dashboard can call.

## Local Config

Copy `config.json` to `config.local.json` for machine-specific values.
Do not commit secrets.

Important fields:

- `bridge_url`: local bridge service, default `http://127.0.0.1:8820`.
- `stream_url`: browser-visible 3D stream URL. Leave empty until Unreal/Pixel Streaming/WebRTC is running.
- `unreal_ws_url`: Unreal-side websocket command endpoint, for example `ws://127.0.0.1:8830/avatar`.
- `runtime_provider`: current target stack, default `web_threejs_runtime`.
- `character_id`: stable id for the 3D digital twin character.

## Pixel Streaming Short Path

The local Pixel Streaming frontend is checked out under:

```text
runtime/avatar-runtime-3d/PixelStreamingInfrastructure
```

Start the signalling/web server:

```powershell
powershell -ExecutionPolicy Bypass -File runtime/avatar-runtime-3d/start_pixel_streaming.ps1
```

This exposes:

```text
Browser player: http://localhost:8080
Unreal streamer URL: ws://127.0.0.1:8888
```

The local dashboard config is:

```json
{
  "bridge_url": "http://127.0.0.1:8820",
  "stream_url": "http://localhost:8080",
  "unreal_ws_url": "",
  "render_transport": "pixel_streaming",
  "character_id": "digital_twin_3d"
}
```

Launch a packaged Unreal app with:

```powershell
YourUnrealApp.exe -PixelStreamingURL=ws://127.0.0.1:8888 -RenderOffScreen
```

For editor play-in-editor testing, enable the Pixel Streaming plugin and use the
same streamer URL in the plugin/runtime settings or launch arguments.

## Web 3D Fallback Runtime

If Unreal is not installed, use the built-in Web 3D runtime:

```text
http://127.0.0.1:8788/avatar-runtime-3d.html
```

Set local config:

```json
{
  "bridge_url": "http://127.0.0.1:8820",
  "stream_url": "http://127.0.0.1:8788/avatar-runtime-3d.html",
  "render_transport": "web_threejs_runtime"
}
```

This runtime:

- renders a persistent browser 3D avatar with Three.js when available;
- falls back to a CSS 3D placeholder instead of showing a blank screen;
- long-polls bridge events through the dashboard;
- plays `audio_url` from `say` events;
- drives mouth movement from audio energy.

This is a temporary local route to validate real-time interaction shape. Replace
the stylized generated avatar with a VRM model later, or switch `stream_url` back
to Pixel Streaming when Unreal/MetaHuman is ready.

## Current Contract

The dashboard sends:

```json
{
  "text": "reply text",
  "audio_url": "/api/avatar3d/streaming-voice?text=...",
  "audio_chunks": [],
  "voice_provider": "volcengine",
  "character_id": "digital_twin_3d"
}
```

The bridge owns mapping that audio into the 3D face/viseme runtime. If no 3D
runtime is connected, the bridge must report that honestly instead of faking a
2D fallback.

## Unreal Integration Step

The first real engine integration is the command channel:

```text
dashboard -> /api/avatar3d/realtime-reply
dashboard -> avatar-3d-bridge /api/say
avatar-3d-bridge -> HTTP event queue / optional UNREAL_WS_URL websocket JSON
Unreal -> state switch + audio playback + Audio2Face input
```

Until `stream_url` is configured, the dashboard will not show a visual stream.
Until `unreal_ws_url` is configured and reachable, the bridge will accept
commands and queue them for Unreal HTTP pull. Once Unreal polls
`/api/unreal/events`, the bridge will report the pull channel as connected.

Minimal Unreal-side loop:

```text
GET  http://127.0.0.1:8820/api/unreal/events?after=<last_event_id>&timeout=10
POST http://127.0.0.1:8820/api/unreal/ack
```

Map `state` events to idle/listening/thinking/speaking animation states. Map
`say` events to audio playback first, then Audio2Face/MetaHuman facial curves.
