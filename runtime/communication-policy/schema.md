# CommunicationPolicy Schema

## 顶层结构

```text
CommunicationPolicy
  version
  generated_at
  modes
  time_policy
  proactive_policy
  passive_response_policy
  relationship_rules
  risk_policy
  news_policy
  calibration_policy
  output_contract
```

## Mode

```text
Mode
  id
  name
  allowed_actions[]
  forbidden_actions[]
  default_for_risk_levels[]
```

允许模式：

- `observe`
- `draft`
- `assist_send`
- `auto_send`

当前 `auto_send` 禁用。

## TimePolicy

```text
TimePolicy
  weekday_windows[]
  weekend_windows[]
  no_cold_start_windows[]
```

时间窗口字段：

- `start`
- `end`
- `allowed_intents[]`
- `disallowed_intents[]`
- `notes`

## ProactivePolicy

```text
ProactivePolicy
  max_daily_suggestions
  triggers[]
  scoring_dimensions[]
  minimum_requirements[]
  message_template
```

默认值：

- `max_daily_suggestions`: 1-3
- `requires_direct_relation`: true
- `requires_topic_match`: true
- `requires_low_disturbance`: true

## PassiveResponsePolicy

```text
PassiveResponsePolicy
  identity_resolution_required
  intent_classes[]
  context_retrieval_required
  draft_structure
```

## RelationshipRule

```text
RelationshipRule
  relationship_type
  tone
  allowed_topics[]
  sensitive_topics[]
  approval_required_for[]
  default_mode
```

## RiskPolicy

```text
RiskPolicy
  levels[]
  escalation_rules[]
  forbidden_actions[]
```

风险等级：

- `R0_safe`
- `R1_low`
- `R2_medium`
- `R3_high`
- `R4_forbidden`

## NewsPolicy

```text
NewsPolicy
  topic_priorities[]
  discussion_output
  contact_matching_rules
```

## CalibrationPolicy

```text
CalibrationPolicy
  daily_questions[]
  feedback_types[]
  update_targets[]
```

反馈类型：

- `confirmed`
- `edited`
- `rejected`
- `not_like_me`
- `too_aggressive`
- `too_soft`
- `wrong_relationship`
- `wrong_topic`
- `privacy_risk`

## OutputContract

每次生成沟通草稿都必须包含：

```text
DraftOutput
  draft_text
  relationship_basis
  topic_basis
  tone_basis
  risk_level
  approval_required
  questions_for_user[]
```
