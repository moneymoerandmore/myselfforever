# Avatar Layer v0.1

第五层对外交互层的本地数字人形象适配。

当前目标分两阶段：

1. `avatar.html` 页面选择联系人，输入对方内容，数字我用现有 `/api/draft` 生成回复，再交给本地头像和声音链路输出。
2. 后续把输入从文本升级为麦克风和摄像头：麦克风走 ASR，摄像头走视觉上下文/表情状态，输出仍复用同一 avatar provider。

## 当前页面

```text
http://127.0.0.1:8788/avatar.html
```

## API

```text
GET  /api/avatar/status
GET  /api/avatar/jobs
POST /api/avatar/reply
```

`/api/avatar/reply` 会：

1. 调用现有草稿生成链路，保留关系画像、SelfCore、CommunicationPolicy 和风险边界。
2. 在 `data/generated/avatar-layer/<job_id>/` 写入 `reply.txt`。
3. 如果配置了本地 TTS，生成 `reply.wav`。
4. 如果配置了 LivePortrait 渲染命令，生成 `avatar.mp4`。

`data/generated/` 已被 `.gitignore` 排除，音视频产物不会进入仓库。

## Stage A: Idle Live Surface

`avatar_stream_worker.py` loops the cached idle video as a local MJPEG stream. This is the first always-on digital-human surface: the page can show a persistent live avatar before any per-message rendering finishes.

Run it with the MuseTalk environment because that environment already has OpenCV:

```powershell
& "D:\AI\MuseTalk\.venv\Scripts\python.exe" runtime\avatar-layer\avatar_stream_worker.py --host 127.0.0.1 --port 8813 --video runtime\avatar-layer\cache\base_idle.mp4
```

Dashboard status reads `stream_worker_url` from `runtime/avatar-layer/config.json` or `AVATAR_STREAM_WORKER_URL`, then exposes `/idle.mjpg` on the avatar page. This is an interim transport. The next step is to replace MJPEG with WebRTC/LiveKit-style frame injection while keeping the same relationship-graph communication core.

## Stage B: Speaking Clip Injection

The stream worker also accepts:

```text
POST /play-video
{"video_path":"D:\\path\\to\\avatar.mp4"}
```

When a MuseTalk job finishes, the dashboard pushes the generated speaking clip to the stream worker. The browser keeps watching the same `/idle.mjpg` live surface; the stream switches from idle to the speaking clip, then returns to idle after the clip ends. This removes the split-brain UI where idle is one surface and speech is a separate video player.

This is still a transitional design: the speaking frames are injected after clip generation, not streamed frame-by-frame as MuseTalk produces them. The final target remains low-latency WebRTC/LiveKit-style frame and audio transport.

## Stage C: Inference Frame Push

The stream worker accepts raw JPEG frames:

```text
POST /push-frame
Content-Type: image/jpeg
<jpeg bytes>
```

During `/realtime-lipsync`, MuseTalk pushes each blended mouth frame to `/push-frame` as soon as it is produced. The MJPEG client keeps the same `/idle.mjpg` connection and shows the latest inference frame while generation is running. If no frame arrives for about two seconds, the stream falls back to the idle video.

This reduces the "nothing happens until mp4 is ready" feeling, but audio is still delivered as a completed WAV/MP4 artifact. True real-time conversation still needs audio streaming plus a WebRTC/LiveKit transport.

## Stage D: Audio-Clock Sync

For lip-sync correctness, the browser must not display pushed frames merely because they arrived. The stream worker now supports sync sessions:

```text
POST /begin-sync
{"session_id":"<avatar-job-id>","fps":25}

POST /push-frame?session_id=<avatar-job-id>&frame_index=42&fps=25
Content-Type: image/jpeg
<jpeg bytes>

GET /sync-frame?session_id=<avatar-job-id>&t=1680
```

The avatar page treats audio as the master clock. It plays the WAV only after a small frame buffer exists, then renders frames to a canvas by `audio.currentTime`. If the target frame has not arrived yet, audio pauses briefly and resumes when the frame is available. This favors mouth/audio sync over raw smoothness.

## Stage E: Low-Latency Avatar Profile

For real-time avatar trials, the dashboard now uses a `fast_avatar` generation profile:

- The relationship-graph draft prompt is constrained to one very short message.
- MuseTalk runs in realtime at `lipsync_fps` 16 by default.
- MuseTalk uses a small realtime batch size (`lipsync_batch_size` 4 by default) so the first frames arrive earlier.
- The worker skips final MP4 muxing (`lipsync_skip_video`, default `true`) and publishes synchronized frames directly to per-audio-chunk sessions.

This reduces perceived latency by shrinking text, audio duration, generated frame count, and post-processing. It does not remove the remaining first-audio bottleneck from IndexTTS2; if the experience is still too slow, the next optimization should target TTS first-token/first-chunk latency or a faster voice path.

## Stage F: Realtime Runtime Lane

The MuseTalk + IndexTTS2 chain is no longer treated as the default interaction path. Local tests showed that even a 3-character utterance can take more than 12 seconds because IndexTTS2 first-audio generation and MuseTalk audio-feature extraction are both blocking.

The avatar layer is now split into two lanes:

- Realtime lane: relationship-graph reply text -> browser/local low-latency speech provider -> lightweight live mouth motion. This is the default for `avatar.html`.
- Fidelity lane: IndexTTS2 + MuseTalk/LivePortrait high-fidelity generation. This remains useful for offline render, replay, and later provider comparison, but it must not block conversation.

Current realtime endpoint:

```text
POST /api/avatar/realtime-reply
GET  /api/avatar/portrait
GET  /api/avatar/streaming-voice?text=...
```

`/api/avatar/realtime-reply` keeps the same SelfCore, identity facts, RelationshipGraph, DyadicProfile, and CommunicationPolicy path as ordinary draft generation. Only the expression provider changes. The temporary browser speech provider does not claim to be the final cloned voice; it is a latency-first placeholder until a true streaming voice provider is selected.

For cloned realtime speech, local private credentials live in `runtime/avatar-layer/config.local.json` and are ignored by git. The current provider contract is:

```json
{
  "realtime_voice_provider": "elevenlabs",
  "elevenlabs_api_key": "...",
  "elevenlabs_voice_id": "...",
  "elevenlabs_model_id": "eleven_flash_v2_5"
}
```

Volcengine is also supported as the realtime voice provider. Use the Ark API-key path when the credential is an `apikey-*` value:

```json
{
  "realtime_voice_provider": "volcengine",
  "volcengine_api_key": "...",
  "volcengine_voice_type": "...",
  "volcengine_model": "...",
  "volcengine_encoding": "mp3"
}
```

For the classic openspeech TTS path, use AppID/Token/Cluster instead:

```json
{
  "realtime_voice_provider": "volcengine",
  "volcengine_app_id": "...",
  "volcengine_token": "...",
  "volcengine_cluster": "...",
  "volcengine_voice_type": "...",
  "volcengine_stream_transport": "websocket",
  "volcengine_ws_endpoint": "wss://openspeech.bytedance.com/api/v1/tts/ws_binary",
  "volcengine_encoding": "mp3"
}
```

When `volcengine_stream_transport` is `websocket`, the dashboard connects to Volcengine's binary WebSocket TTS endpoint and proxies the audio frames back through `/api/avatar/streaming-voice`. Successful responses include `X-Voice-Transport: volcengine-websocket`. If the WebSocket path fails before audio starts, the server falls back to the proven JSON/base64 HTTP TTS path.

When the selected provider has both credentials and a voice identifier configured, `avatar.html` plays the cloned voice from `/api/avatar/streaming-voice`. Realtime replies also return `clone_voice.audio_chunks`; each chunk has its own `visual_session_id`, and the page requests `/sync-frame?session_id=...&t=...` from the stream worker using the currently playing audio time. This keeps cloned speech and MuseTalk frames on the same browser clock while preloading the next speech chunk. If the voice identifier is missing, the page falls back to browser speech rather than pretending a generic voice is the user's clone.

## 环境变量契约

### 头像图

```powershell
$env:DIGITAL_TWIN_AVATAR_IMAGE="D:\path\to\portrait.png"
```

建议使用清晰正脸或半身头像，光线稳定，脸部无遮挡。

### 声音 TTS

```powershell
$env:DIGITAL_TWIN_TTS_COMMAND="python D:\path\to\tts_adapter.py --text {text_path} --out {audio_path}"
```

命令需要读取 `{text_path}`，输出 PCM/WAV 到 `{audio_path}`。

可用占位符：

- `{text_path}`
- `{audio_path}`
- `{job_dir}`

## IndexTTS2 适配

官方仓库：

```text
https://github.com/index-tts/index-tts
```

建议把 IndexTTS2 clone 到项目外的大模型目录，例如：

```text
D:\AI\index-tts
```

把你的声音参考音频放到本项目的本地 runtime 目录，例如：

```text
D:\Users\cloud\Documents\数字永生\runtime\avatar-layer\voice_ref.wav
```

参考音频建议：

- 10-30 秒
- 单人
- 无背景音乐
- 无混响和明显噪声
- 语速、语气尽量像你日常说话

官方 IndexTTS2 使用 `uv` 管理环境。安装与模型下载在 IndexTTS2 仓库里执行：

```powershell
cd D:\AI\index-tts
git lfs install
git lfs pull
uv sync --all-extras
uv tool install "modelscope"
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
```

Windows 上如果 DeepSpeed 难装，可以先不用 `--all-extras`，只跑基础推理链路；跑通优先，优化靠后。

本项目已经提供薄适配器：

```text
runtime/avatar-layer/indextts2_adapter.py
```

配置 TTS 命令时，用 IndexTTS2 的 `uv run` 来执行这个适配器：

```powershell
$env:DIGITAL_TWIN_TTS_COMMAND="cd /d D:\AI\index-tts && uv run python D:\Users\cloud\Documents\数字永生\runtime\avatar-layer\indextts2_adapter.py --repo D:\AI\index-tts --voice D:\Users\cloud\Documents\数字永生\runtime\avatar-layer\voice_ref.wav --text {text_path} --out {audio_path} --fp16"
```

如果显卡或 CUDA 报错，先去掉 `--fp16`：

```powershell
$env:DIGITAL_TWIN_TTS_COMMAND="cd /d D:\AI\index-tts && uv run python D:\Users\cloud\Documents\数字永生\runtime\avatar-layer\indextts2_adapter.py --repo D:\AI\index-tts --voice D:\Users\cloud\Documents\数字永生\runtime\avatar-layer\voice_ref.wav --text {text_path} --out {audio_path}"
```

可选情绪控制：

```powershell
--emotion-text "自然、短句、略带判断感，但不要夸张" --emotion-alpha 0.6
```

### LivePortrait 渲染

```powershell
$env:LIVEPORTRAIT_RENDER_COMMAND="python D:\path\to\liveportrait_adapter.py --image {image_path} --audio {audio_path} --text {text_path} --out {output_path}"
```

命令需要读取头像图和音频，输出 mp4 到 `{output_path}`。

可用占位符：

- `{image_path}`
- `{audio_path}`
- `{text_path}`
- `{output_path}`
- `{job_dir}`

## 适配原则

- 数字我大脑仍在本项目：关系、风格、事实审计和风险边界不下放给 LivePortrait。
- LivePortrait 只负责形象层，不负责“像不像我地判断该说什么”。
- 第一阶段只处理文本输入；麦克风和摄像头会作为输入层升级，不改 avatar provider 的输出接口。
- 自动发送和真实对外交互仍受 CommunicationPolicy 约束；形象层完成不等于自动授权。
## Architecture Boundary: Relationship Core First

Avatar is a multimodal input/output surface for the existing relationship-graph communication system. It must not become an independent chat logic.

Runtime order:

1. Resolve the person or group context from `RelationshipGraph`.
2. Build conversation history using the same role structure as the main dashboard.
3. Generate the reply through the existing `/api/draft` path, using `SelfCore`, identity facts, `RelationshipGraph`, `DyadicProfile`, and `CommunicationPolicy`.
4. Pass only the approved draft text to TTS and lip-sync.
5. Render voice/video as output artifacts.

Microphone and camera input should enter the same pipeline: ASR, visual context, and emotion cues are input evidence for relationship-aware generation, not a separate persona or standalone assistant.
