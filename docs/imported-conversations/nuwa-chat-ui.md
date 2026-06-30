# Nuwa 本地服务接手卡

## 来源

- 源会话：用户界面
- Thread ID：`019eb029-5ea6-7981-b90b-4cfa1368bf38`
- 源目录：`C:\Users\cloud\Documents\Codex\2026-06-02\skill-https-github-com-alchaincyf-nuwa`
- 服务目录：`C:\Users\cloud\Documents\Codex\2026-06-02\skill-https-github-com-alchaincyf-nuwa\outputs\nuwa-chat`

## 启动服务

```powershell
cd C:\Users\cloud\Documents\Codex\2026-06-02\skill-https-github-com-alchaincyf-nuwa\outputs\nuwa-chat
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" server.js
```

浏览器打开：

```text
http://localhost:8787/
```

API key 可以在网页里填写。若提示端口占用，通常表示服务已经在运行，直接刷新网页即可。

## 当前目录内相关文件

- `server.js`
- `app.js`
- `index.html`
- `styles.css`
- `README.md`
- `WECHAT_FILTER.md`
- `personal-skill-work`
- `personal-skill-work-v2`
- `personas`

## 下一步

- 判断是否把 Nuwa UI 作为本项目的交互入口
- 把个人 skill v0.1 接入本地服务
- 增加项目首页：关系图谱、主动聊天、蒸馏状态、skill 测试入口
