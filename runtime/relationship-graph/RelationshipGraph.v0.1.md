# RelationshipGraph v0.1

## 版本信息

- 版本：`RelationshipGraph v0.1`
- 生成时间：2026-06-10
- 来源：现有关系链图谱输出、关系维度表、称呼候选表、身份别名表、接手摘要
- 主输出源目录：`C:\Users\cloud\Documents\Codex\2026-06-09\new-chat\outputs`

## 当前图谱规模

- People：845
- Nodes：846
- Links：2041
- 直接微信关系：100
- 被提及人物：745

## 当前关系分布

全部人物：

| 客观关系 | 数量 |
| --- | ---: |
| 间接提及人物 | 703 |
| 同事/前同事 | 75 |
| 同学/校友 | 43 |
| 服务/事务协作 | 12 |
| 亲人/核心家庭 | 5 |
| 亲戚/家族 | 3 |
| 姻亲/配偶家人 | 3 |
| 朋友 | 1 |

直接微信关系：

| 客观关系 | 数量 |
| --- | ---: |
| 同事/前同事 | 71 |
| 同学/校友 | 21 |
| 亲戚/家族 | 3 |
| 亲人/核心家庭 | 3 |
| 服务/事务协作 | 1 |
| 朋友 | 1 |

## 关系图谱的定位

这个图谱不是通讯录，也不是社交网络可视化玩具。它是数字分身对外沟通时的关系记忆系统。

它需要支持：

- 被动响应：别人发来消息时，知道对方是谁、什么关系、怎么称呼、常聊什么、什么不能说。
- 主动沟通：判断今天是否适合找某个人聊，聊什么，打扰成本多大。
- 关系校对：让我修正身份、称呼、关系、共同话题和边界。
- 证据追溯：每个称呼、关系和话题都能回到证据等级。
- 风险控制：不能因为“被提及很多”就主动联系或暴露隐私。

## 核心对象

### PersonNode

表示一个真实人物或暂未合并的身份节点。

关键字段：

- `person_id`
- `display_name`
- `call_name`
- `wechat_name`
- `node_type`
- `objective_relationship`
- `relationship_positioning`
- `identity_confidence`
- `call_name_confidence`
- `relationship_confidence`
- `topic_profile`
- `communication_profile`
- `permission_profile`
- `evidence_refs`

### RelationshipEdge

表示我和某人的关系，或人与人之间在图谱里的关联。

关键字段：

- `source`
- `target`
- `edge_type`
- `weight`
- `evidence_type`
- `evidence_refs`
- `risk_notes`

### TopicProfile

表示我和某个人或某个圈层常聊什么。

当前已有高频主题字段，后续应拆成：

- `work_product`
- `investment`
- `ai_technology`
- `housing_decoration`
- `family_parenting`
- `pet_life`
- `dining_social`
- `medical_health`
- `gaming_entertainment`
- `news_politics`
- `other`

### CommunicationProfile

表示和某个人怎么聊。

建议字段：

- `tone`
- `message_density`
- `humor_level`
- `directness`
- `initiative_level`
- `common_openers`
- `avoid_topics`
- `recent_context`
- `last_verified_at`

### PermissionProfile

表示数字分身能做什么。

默认权限：

- `can_retrieve_context`: true
- `can_generate_draft`: true for direct WeChat relations, false/limited for mentioned-only people
- `can_proactively_suggest`: true only for direct relations with clear relationship and topic
- `can_auto_send`: false
- `requires_user_approval`: true

## 分类原则

关系分类使用客观现实关系，而不是兴趣或话题。

优先级：

1. 亲人/核心家庭
2. 亲戚/家族
3. 姻亲/配偶家人
4. 同事/前同事
5. 同学/校友
6. 服务/事务协作
7. 朋友
8. 间接提及人物
9. 其他

关键规则：

- 如果一个人是同事，不因为常聊投资就改成投资圈。
- 如果一个人是同学，不因为常聊买房就改成买房圈。
- 兴趣/活动圈层是第二维度，不覆盖客观关系。
- 被提及人物不是可主动沟通对象，除非用户确认其真实关系和联系方式。

## 称呼规则

数字分身必须尽量使用“我真实会用的称呼”，而不是微信昵称。

称呼证据等级：

### `locked`

用户确认或人工锁定。

可以直接用于展示和草稿。

### `strong`

来自强证据：

- 我直接称呼对方
- `@` 后明确称呼
- 引用回复中明确对对方使用称呼
- 对方自我介绍
- 稳定旧群名或长期称呼

可以用于展示，但高风险沟通仍建议确认。

### `candidate`

来自候选表或邻近上下文。

只能作为审计候选，不直接用于草稿。

### `unsafe`

可能是上下文短语、第三人称、亲属代词、动作短语或误识别。

例如候选表里可能出现“我妈”“阿姨”“帮我妈”这类并非对方称呼的短语。

不能直接使用。

## 身份合并规则

身份合并是高风险操作。

允许合并的证据：

- 同账号或同 user id
- 现有 alias map 有明确证据
- 聊天内容明确说明两个名字是同一人
- 多次高度具体的自我指认

禁止合并：

- 只因为称呼相同
- 只因为都叫某个亲属称谓
- 只因为同群出现
- 只因为共同话题相似
- 只因为模型猜测

当前策略：

- 默认保守。
- `ADDITIONAL_ALIAS_MAP` 保持空或极小。
- 合并前先进入 `merge_candidate`，必须可审计。

## 运行时检索能力

数字分身需要以下查询能力：

### `resolve_person(query)`

输入昵称、称呼、微信名或上下文，返回候选人物。

必须返回：

- 候选列表
- 置信度
- 是否需要用户确认
- 不合并原因

### `get_relationship_context(person_id)`

返回我和这个人的关系上下文。

必须包含：

- 客观关系
- 关系定位
- 主要场景
- 共同话题
- 称呼建议
- 风险提示

### `get_conversation_strategy(person_id, intent)`

返回沟通策略。

必须包含：

- 建议语气
- 是否适合主动
- 可聊话题
- 避免话题
- 是否需要我确认

### `score_proactive_candidate(person_id, trigger)`

判断是否适合主动联系。

评分维度：

- 关系强度
- 近期互动
- 共同话题相关性
- 新闻/事件相关性
- 打扰成本
- 敏感风险
- 我是否通常会主动聊这类话题

### `audit_relationship_graph()`

持续审计图谱质量。

必查项目：

- `call_name == wechat_name`
- 英文名
- `wxid_*`
- 长抽象昵称
- 没有称呼证据的人
- 自动身份合并
- 直接关系但没有沟通画像的人

## 对外沟通基线

### 亲人/核心家庭

特点：

- 上下文密度高
- 情绪风险高
- 边界和责任议题多

规则：

- 只生成草稿，不自动发送。
- 家庭冲突、教育、照护、金钱相关内容必须确认。
- 可以保留温度，但要避免替我情绪化升级。

### 同事/前同事

特点：

- 常涉及工作、产品、组织、投资、行业判断。
- 可以更直接、更目标导向。

规则：

- 适合生成分析型草稿。
- 涉及公司、项目、敏感内部信息时必须脱敏和确认。
- 不跨上下文泄露其他群聊信息。

### 同学/校友

特点：

- 常兼具朋友、生活、投资、买房、科技讨论。

规则：

- 适合主动聊共同兴趣。
- 注意不要把工作语气带得太重。
- 投资相关内容默认只做观点讨论，不做建议承诺。

### 服务/事务协作

特点：

- 目标明确，边界清晰。

规则：

- 语气应精确、简洁、少玩笑。
- 明确需求、时间、责任。
- 不使用亲密关系上下文。

### 间接提及人物

特点：

- 不一定是直接联系人。
- 可能只是聊天中多次出现。

规则：

- 只能用于理解上下文。
- 不主动联系。
- 不生成假装熟悉的消息。
- 如需使用，必须先让我确认身份和关系。

## 当前质量判断

稳定部分：

- 图谱已可用并通过验证。
- 直接关系和间接提及已分开。
- 客观关系优先级已经明确。
- 关系维度表已有可用字段。

薄弱部分：

- 称呼证据覆盖不足：845 人里只有 83 人有非空称呼证据。
- 663 人 `称呼名 == 微信名`，其中很多需要审计。
- 显式称呼候选仍有误识别短语。
- 身份合并必须继续保守。
- 沟通权限和主动沟通策略尚未落表。

## RelationshipGraph v0.2 前置任务

1. 生成机器可读 schema。
2. 给 100 个直接关系补充 `communication_profile`。
3. 对 top 100 展示名做称呼审计。
4. 给所有被提及人物设置默认权限：不可主动、不可假装熟悉。
5. 增加主动沟通评分函数。
6. 增加关系图谱回归检查。
7. 与 `SelfCore v0.1` 联动，生成关系感知回复草稿。
