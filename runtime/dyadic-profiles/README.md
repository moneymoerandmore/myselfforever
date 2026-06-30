# Dyadic Profiles

`DyadicProfile` 描述的不是“我一般怎么说话”，而是“我面对某一个具体的人时，会呈现出怎样的沟通表现型”。

它位于 `SelfCore`、`RelationshipGraph` 和 `CommunicationPolicy` 之间：

- `SelfCore`：跨关系稳定的价值观、思维方式和表达机制。
- `RelationshipGraph`：对方是谁、真实关系、称呼和共同场景。
- `DyadicProfile`：我和这个人具体聊什么、怎么聊、什么时候聊、谁更常主动。
- `CommunicationPolicy`：这次允许做什么、风险多高、是否需要确认。

生成优先级：

```text
当前消息与近期上下文
  > DyadicProfile(person_id)
  > SceneProfile(group_or_private)
  > SelfCore
  > 通用模型先验
```

没有足够双人样本时必须降级并显示置信度，不能用“家人风格”“同事风格”等大类模板伪装成个人画像。

## 数据边界

- 原始聊天只从本地源目录读取。
- 项目内只保存聚合指标、主题计数、风格机制和证据数量。
- 不保存完整聊天原文，不保存可连续还原对话的样本。
- 私聊是强证据；群聊只有明确引用、@ 或直接定向证据才进入双人画像。

