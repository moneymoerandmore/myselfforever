# 关系链图谱接手卡

## 来源

- 源会话：关系链梳理
- Thread ID：`019eb029-8f5e-7f11-8c13-cb98104f3a54`
- 源目录：`C:\Users\cloud\Documents\Codex\2026-06-09\new-chat`
- 输出目录：`C:\Users\cloud\Documents\Codex\2026-06-09\new-chat\outputs`
- 原始数据：`C:\tmp\wechat-raw`

## 当前可用产物

- 主图谱：`C:\Users\cloud\Documents\Codex\2026-06-09\new-chat\outputs\relationship_graph.html`
- 接手摘要：`C:\Users\cloud\Documents\Codex\2026-06-09\new-chat\outputs\relationship_graph_handoff_summary.md`
- 人物维度表：`relationship_dimensions.csv`
- 身份别名表：`identity_alias_map.json`
- 被提及人物节点：`mentioned_relationship_nodes.json`
- 显式称呼候选：`explicit_call_name_candidates.csv`
- 宽松称呼候选：`call_name_candidates.csv`

## 当前状态

图谱已可用并通过验证。

- People：845
- Nodes：846
- Links：2041

## 构建与验证

构建命令：

```powershell
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" work\build_relationship_graph.py
```

验证命令：

```powershell
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" work\validate_relationship_graph.js
```

## 关键规则

关系分类优先使用客观现实关系，不优先按兴趣或聊天主题分类。

优先级：

1. 直系家庭 / 核心家庭
2. 正式亲属 / 扩展家庭
3. 姻亲 / 配偶家庭
4. 同事 / 前同事
5. 同学 / 校友
6. 服务 / 实务协作
7. 朋友
8. 间接提及人物
9. 其他

## 高风险点

- 不要因为称呼相同就合并身份。
- 不要把投资、吃饭、游戏、AI、买房等话题当作主关系分类。
- 称呼必须来自强证据：直接称呼、`@`、引用回复、稳定旧群名、自我介绍。
- `ADDITIONAL_ALIAS_MAP` 当前故意为空，新增身份合并必须有强证据。

## 下一步

- 迁入 `work\build_relationship_graph.py` 和 `work\validate_relationship_graph.js`
- 为节点、边、证据、身份合并建立 schema
- 审计 top 100 显示名
- 对英文名、`wxid_*`、长抽象昵称、`callName == wechatName` 的人物做专项检查
