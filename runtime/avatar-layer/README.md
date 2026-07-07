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
