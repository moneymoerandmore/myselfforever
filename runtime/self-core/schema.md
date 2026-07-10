# SelfCore Schema

这是 `SelfCore` 的结构设计。后续可转成 JSON/YAML。

## 顶层字段

```text
SelfCore
  version
  generated_at
  source_manifest
  identity_thesis
  identity_facts[]
  worldview[]
  lifeview[]
  values[]
  thinking_models[]
  decision_heuristics[]
  expression_dna
  communication_baseline
  anti_patterns[]
  update_policy
  evidence_index[]
```

## 字段说明

### `identity_thesis`

一句话人格假设。

字段：

- `statement`
- `confidence`
- `notes`

### `identity_facts[]`

稳定身份事实。用于约束数字我可以或不可以认领的能力、偏好、生活约束、角色身份和承诺边界。

落点：
- `runtime/self-core/identity-facts/facts.jsonl`
- `runtime/self-core/identity-facts/corrections.jsonl`
- `runtime/self-core/identity-facts/candidates.jsonl`

字段：
- `id`
- `fact_type`
- `polarity`
- `statement`
- `runtime_rule`
- `confidence`
- `source_type`
- `evidence_refs`
- `confirmed_by_user`
- `status`

### `worldview[]`

世界如何运转。

字段：

- `id`
- `claim`
- `behavioral_rule`
- `confidence`
- `evidence_refs`

### `lifeview[]`

人生、成长、意义、目标。

字段：

- `id`
- `claim`
- `implication`
- `confidence`
- `evidence_refs`

### `values[]`

什么重要、什么是底线、什么值得。

字段：

- `id`
- `value`
- `positive_behavior`
- `negative_behavior`
- `confidence`
- `evidence_refs`

### `thinking_models[]`

可运行的拆解模型。

字段：

- `id`
- `name`
- `trigger`
- `steps`
- `failure_mode`
- `evidence_refs`

### `decision_heuristics[]`

短规则。

字段：

- `id`
- `rule`
- `applies_to`
- `risk`

### `expression_dna`

表达方式。

字段：

- `sentence_shape`
- `common_moves`
- `tone`
- `allowed_mimicry`
- `forbidden_mimicry`
- `relationship_variants`

### `communication_baseline`

对外沟通基线。

字段：

- `passive_response_policy`
- `proactive_policy`
- `approval_required`
- `risk_levels`

### `anti_patterns[]`

边界和反模式。

字段：

- `id`
- `pattern`
- `risk`
- `runtime_guardrail`
- `evidence_refs`

### `update_policy`

自进化规则。

字段：

- `fast_update`
- `multi_evidence_update`
- `user_confirmed_update`
- `rollback_policy`

### `evidence_index[]`

证据索引，不保存长原文。

字段：

- `episode_id`
- `bucket`
- `source_file`
- `reason_used`
- `privacy_level`
