# DyadicProfile Schema

```text
DyadicProfile
  profile_id
  person_key
  canonical_name
  aliases[]
  evidence
  coverage
  topics
  interaction_pattern
  expression_pattern
  temporal_pattern
  channel_pattern
  confidence
  update_policy
```

## Evidence

```text
EvidenceSummary
  private_session_count
  private_outgoing_count
  private_incoming_count
  group_directed_outgoing_count
  group_directed_incoming_count
  group_context_count
  first_interaction_at
  last_interaction_at
  source_files[]
```

证据强度：

- `private_direct`: 私聊，强证据。
- `group_quoted_reply`: 群聊中明确引用对方，强定向证据。
- `group_at_mention`: 群聊中明确 @ 对方，中强证据。
- `group_context`: 同群共现但没有定向证据，只能进入场景画像。

## Topics

```text
TopicProfile
  shared_topics[]
  my_outgoing_topics[]
  their_incoming_topics[]
  topic_distribution{}
  topic_diversity
```

主题必须绑定具体对象，不能只从全局兴趣迁移。

## Interaction Pattern

```text
InteractionPattern
  initiation_ratio
  reply_ratio
  median_reply_seconds
  average_burst_size
  max_burst_size
  question_ratio
  acknowledgement_ratio
  link_or_media_response_ratio
```

## Expression Pattern

```text
ExpressionPattern
  average_chars
  median_chars
  short_message_ratio
  multi_message_burst_ratio
  question_marker_ratio
  exclamation_ratio
  laughter_ratio
  emoji_or_bracket_ratio
  judgment_marker_ratio
  boundary_marker_ratio
  action_marker_ratio
  uncertainty_marker_ratio
  dominant_mechanisms[]
```

这里描述表达机制，不保存原句模板。

## Temporal Pattern

```text
TemporalPattern
  hour_distribution{}
  active_windows[]
  weekday_ratio
  weekend_ratio
  late_night_ratio
```

## Channel Pattern

```text
ChannelPattern
  private_ratio
  group_directed_ratio
  preferred_contexts[]
  group_scene_profiles[]
```

## Confidence

```text
Confidence
  level
  score
  reasons[]
  limitations[]
```

建议等级：`high`, `medium`, `low`, `insufficient`。

## 更新规则

- 新消息可以快速更新计数、时间分布和话题分布。
- 表达机制需要至少 50 条定向文本样本后才进入 `medium`。
- 私聊不足时，群聊定向回复不能冒充完整双人画像。
- 用户对草稿的编辑和“不像我”反馈，优先更新对应 `person_key`，不能直接改写全局 `SelfCore`。

