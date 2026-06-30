# WeChat Bridge

Windows PC 微信的本地旁路伴随服务。当前阶段只读取/接收群消息、维护多轮上下文并生成待审草稿，不执行发送。

## 安全边界

- 不保存微信账号密码和登录凭证。
- 不做 DLL 注入、进程内存读取或协议逆向。
- `auto_send` 不存在于当前服务接口。
- 群消息运行数据写入 `data/generated/wechat-bridge/`，由 `.gitignore` 排除。
- Poe API Key 只随单次生成请求转发，不写入磁盘。

## 启动

```powershell
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" services\wechat-bridge\launch_bridge.py
```

默认地址：

```text
http://127.0.0.1:8790/
```

## 当前流程

1. 启动只读监听配置，指定群名和自己的群昵称。
2. `window_capture_ocr` 通过离屏窗口截图 + 本地 OCR 读取群消息；测试接口也可以手动写入消息。
3. 服务按群保存最近 80 条多轮上下文。
4. 目标群可配置为更积极的 `trigger_all`，或仅在 `@我`、关键词命中时创建待审项。
5. 调用 Dashboard 的 `/api/draft`，使用完整群上下文生成回复。
6. 草稿进入审核队列，不发送微信；当前版本不做前台激活、点击输入框或自动发送。

## API

```text
GET  /api/health
GET  /api/status
GET  /api/events?group=群名
GET  /api/reviews
GET  /api/wechat/probe
POST /api/watch/start
POST /api/watch/stop
POST /api/events
POST /api/reviews/generate
POST /api/reviews/decision
```

启动监听：

```json
{
  "groups": ["测试群"],
  "self_names": ["我的群昵称"],
  "keywords": ["AI", "项目"],
  "adapter": "window_capture_ocr",
  "trigger_all": true,
  "auto_reply": false
}
```

写入一条测试消息：

```json
{
  "group": "测试群",
  "sender": "张三",
  "content": "@我的群昵称 你怎么看？"
}
```

安装可选的微信窗口探测依赖后，`GET /api/wechat/probe` 会列出新版微信可访问性控件：

```powershell
python -m pip install -r services\wechat-bridge\requirements.txt
```

当前机器上的新版微信主窗口使用自绘画布，UI Automation 只能看到 `MMUIRenderSubWindowHW` 容器，不能直接读取消息文本。当前采用本地离屏截图与 OCR 只读识别；不会改用进程注入或内存读取。

Dashboard 顶部的按钮现在是开关：

- `只读`：开始 OCR 读取目标群新消息，不生成也不发送。
- `自动草稿`：读取新消息后调用模型生成草稿，进入审核队列，不发送。
- `自动发送`：低风险新消息生成草稿后，只在当前前台已经是 PC 微信输入框时粘贴并回车；不主动切换窗口、不点击输入框。投资、金额、承诺、隐私等内容仍会拦截。
- `停止监控`：停止 OCR 线程，Bridge 服务仍保留在本机等待下次启动。

当前只处理互动文字消息。图片、视频、表情、文件、链接卡片、截图中的长文字和系统提示都会在 OCR 层过滤，不进入模型。

自动回复不是逐条抢答：

- 新文字先进入待回复队列。
- 默认等待 10 秒，如果群里连续短句还在出现，就继续合并上下文。
- 回复一次后默认冷却 90 秒；冷却期只记录消息，不再次响应。
