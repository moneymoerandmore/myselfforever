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

本项目最终要初始化并持续进化一个以“我”为核心的数字分身：它理解我的三观、思维方式、表达习惯、关系链和日常话题，能和我校对，也能在受控权限下对外进行主动和被动沟通。
