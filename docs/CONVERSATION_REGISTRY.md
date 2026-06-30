# 迁入对话索引

这个文件记录已经从本地 Codex 会话迁入项目索引的工作。这里的“迁入”指：把目标、状态、关键产物、源路径和下一步写入本项目，方便后续在同一个仓库里继续推进。

## 总览

| 工作流 | 源会话 | Thread ID | 源目录 | 当前状态 |
| --- | --- | --- | --- | --- |
| 关系链图谱 | 关系链梳理 | `019eb029-8f5e-7f11-8c13-cb98104f3a54` | `C:\Users\cloud\Documents\Codex\2026-06-09\new-chat` | 可用，已有 validated HTML graph |
| 主动聊天模型 | 主动发起聊天话题特征 | `019eb029-83ba-7891-9d36-26d84b78e923` | `C:\Users\cloud\Documents\Codex\2026-06-08\new-chat` | 已有 Markdown 分析与一周执行计划 |
| 个人 skill 蒸馏 | 三观梳理 | `019eb029-76fb-7340-8c98-af43bc3757cc` | `C:\Users\cloud\Documents\Codex\2026-06-03\skill` | 已完成语料分层和蒸馏指令 |
| Nuwa 本地 UI | 用户界面 | `019eb029-5ea6-7981-b90b-4cfa1368bf38` | `C:\Users\cloud\Documents\Codex\2026-06-02\skill-https-github-com-alchaincyf-nuwa` | 服务可启动，端口 `8787` |
| 数字永生主线 | 架构、Dashboard、关系页、Poe 生成、多轮模拟、微信桥接 | `019eb56b-490c-7242-8a58-dcb2ba91cb0c` / 恢复副本 `019eb60b-1090-7e60-a043-0d400dbfd7fe` | `D:\Users\cloud\Documents\数字永生` | 已 fork 成可见置顶副本，项目产物已落盘；微信桥接需继续迭代 |
| Codex 会话恢复 | 恢复 Codex session | `019eb01f-8e8c-7b01-8cf0-8a2ffe5a8789` | `C:\Users\cloud\Documents\Codex\2026-06-10\c-users-cloud-codex-session` | 旧会话已 fork 成可见副本 |
| 早期环境准备 | 清洗我的微信聊天记录 | `019eb029-6c4a-7b33-b192-1926276e9eaa` | `C:\Users\cloud\Documents\Codex\2026-06-02\new-chat` | 记录了 Git 安装与早期准备 |

## 迁移策略

当前不把大体量数据复制进仓库，避免混入隐私原始数据和百 MB 级 JSONL。优先迁入：

- 每条会话的目标和当前状态
- 关键输出文件路径
- 可复现命令
- 已知风险和用户偏好
- 下一步行动

## 统一项目方向

这些会话可以收束成一个主线：

从微信聊天记录中抽取“我是谁、我怎么想、我和谁有关、我会怎么说话”，最终形成一个可持续更新的个人数字化系统。

核心模块：

- 记忆层：清洗后的 episode、关系链、人物画像、时间线
- 认知层：三观骨架、判断启发式、表达 DNA、反模式
- 交互层：主动聊天、关系上下文引用、个人 skill / agent
- 工具层：本地网页、图谱浏览、语料审计、蒸馏流水线
