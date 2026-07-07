# Dashboard

本地数字分身 dashboard。

当前版本提供一个草稿生成页面：

- 从关系链下拉选择联系人
- 按称呼、微信名、关系、主题过滤联系人
- 输入场景
- 选择意图
- 输出草稿、关系依据、话题依据、风险等级和确认项
- 从 `DyadicProfile` 加载该联系人的专属话题、节奏、主动性和表达机制
- 正文强制通过 Poe 模型生成；规则层只负责身份、关系、风险和上下文组装
- 多模态材料摄入已拆到独立页面：图片直接压缩，视频/录屏在浏览器本地抽帧，只把抽样帧和说明送入模型

## 启动

```powershell
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" apps\dashboard\launch_dashboard.py
```

浏览器打开：

```text
http://127.0.0.1:8788/
```

多模态摄入独立页：

```text
http://127.0.0.1:8788/multimodal.html
```

数字人形象页：

```text
http://127.0.0.1:8788/avatar.html
```

该页属于第五层对外交互层。当前第一阶段支持“选择联系人 + 输入对方内容 -> 生成我的回复 -> 交给本地 LivePortrait/TTS 适配器”；本地适配契约见 `runtime/avatar-layer/README.md`。

## API

健康检查：

```text
GET /api/health
```

关系链联系人：

```text
GET /api/people
```

生成草稿：

```text
POST /api/draft
```

请求：

```json
{
  "query": "联系人",
  "scenario": "场景",
  "intent": "work_discussion",
  "mode": "draft"
}
```

多模态材料摄入：

```text
POST /api/multimodal/intake
```

请求：

```json
{
  "target": "self_understanding",
  "media_kind": "video_sampled_frames",
  "source_name": "screen-recording.mp4",
  "note": "这张截图代表我最近关注的话题",
  "context": "今天的内容消费和判断",
  "timeline_text": "00:12 暂停在某个观点并补充反驳",
  "video_metadata": {
    "duration_seconds": 1800,
    "width": 1920,
    "height": 1080,
    "sampling_strategy": "uniform-local-browser-sampling"
  },
  "files": [
    {
      "name": "screen-recording-t00:12.jpg",
      "type": "image/jpeg",
      "size": 12345,
      "timestamp_seconds": 12,
      "data_url": "data:image/jpeg;base64,..."
    }
  ]
}
```

该接口只把材料整理为候选记录，保存到 `data/generated/multimodal-intake/`。它不会直接改写 `SelfCore`、关系链或自动发送策略。长视频不应直接上传原始文件；独立页会在浏览器本地抽取有限关键帧并压缩后再提交。

数字人形象层：

```text
GET  /api/avatar/status
GET  /api/avatar/jobs
POST /api/avatar/reply
```

`/api/avatar/reply` 会复用 `/api/draft` 的回复生成结果，再按本地环境变量调用 TTS 和 LivePortrait 命令。未配置本地命令时，接口仍会创建任务并返回缺失项，不会伪造视频输出。
