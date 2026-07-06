# 数字永生项目

> Codex / AI agent 接手本项目时，应先阅读 [`AGENTS.md`](AGENTS.md)。

这个仓库用于把此前分散在多个 Codex 本地会话里的工作收束成一个可持续推进的项目。

当前已迁入索引的主题包括：

- 微信聊天记录清洗与蒸馏语料分层
- 个人思维方式 / 表达方式 skill 蒸馏
- 社会关系与关系链图谱
- 主动发起聊天的话题、时间和风格模型
- Nuwa skill / 本地网页服务
- Codex 旧会话恢复与迁移记录

## 项目入口

- [Agent 常驻入口](AGENTS.md)
- [数字分身项目架构](docs/ARCHITECTURE.md)
- [迁入对话索引](docs/CONVERSATION_REGISTRY.md)
- [项目路线图](docs/NEXT_ACTIONS.md)
- [SelfCore v0.1](runtime/self-core/SelfCore.v0.1.md)
- [RelationshipGraph v0.1](runtime/relationship-graph/RelationshipGraph.v0.1.md)
- [CommunicationPolicy v0.1](runtime/communication-policy/CommunicationPolicy.v0.1.md)
- [最小草稿生成器](tools/draft-generator/README.md)
- [本地 Dashboard](apps/dashboard/README.md)
- [PC 微信旁路伴随服务](services/wechat-bridge/README.md)
- [关系链图谱接手卡](docs/imported-conversations/relationship-graph.md)
- [主动聊天模型接手卡](docs/imported-conversations/proactive-conversation.md)
- [个人 skill 蒸馏接手卡](docs/imported-conversations/personal-skill-distillation.md)
- [Nuwa 本地服务接手卡](docs/imported-conversations/nuwa-chat-ui.md)
- [Codex 会话恢复记录](docs/imported-conversations/codex-session-recovery.md)

## 当前原则

原始聊天记录和大型派生数据暂不复制进仓库。这个仓库先保存项目结构、索引、决策记录、接手说明和后续推进计划。

大型数据源仍保留在本机原路径，例如：

- `C:\tmp\wechat-raw`
- `C:\Users\cloud\Documents\Codex\2026-06-03\skill\outputs`
- `C:\Users\cloud\Documents\Codex\2026-06-09\new-chat\outputs`

后续如果需要沉淀可复现流水线，再把脚本、小样本、schema、配置和脱敏测试数据迁入本仓库。

## 北极星

本项目最终要初始化并持续进化一个以“我”为核心的数字我。

数字我的核心是本我：三观、判断方式、价值排序、表达 DNA 和边界，沉淀在 `SelfCore`。

数字我的外显是表我：不同人眼里的我不同，因为社会关系、亲密度、共同经历、表达原则和沟通风格不同，沉淀在 `RelationshipGraph`、`DyadicProfile` 和 `CommunicationPolicy`。

微信聊天记录、多模态材料、每日新闻和用户反馈都是现实输入。它们先形成证据和候选，再经过真我校对，持续反馈到 `SelfCore`、关系图谱和沟通策略。

对外交互层让数字我逐步参与现实生活：群聊被动回复、私聊草稿、主动发起话题和低风险自动发送。但真我的矫正权始终最高，任何不像我、事实错误或越界的行为都必须回流修正。
