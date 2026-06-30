# RelationshipGraph Schema

这是关系链图谱的结构设计。后续可转成 JSON/YAML/SQLite 表。

## 顶层结构

```text
RelationshipGraph
  version
  generated_at
  source_manifest
  people[]
  edges[]
  aliases[]
  audit
  update_policy
```

## PersonNode

```text
PersonNode
  person_id
  display_name
  call_name
  wechat_name
  canonical_name
  node_type
  objective_relationship
  relationship_positioning
  interest_circles[]
  main_scenes[]
  frequent_topics[]
  identity_confidence
  call_name_confidence
  relationship_confidence
  topic_confidence
  dyadic_profile_ref
  permission_profile
  evidence_refs[]
  risk_notes[]
  last_verified_at
```

## 字段说明

### `node_type`

允许值：

- `direct_wechat_relation`
- `mentioned_only`
- `merged_identity`
- `unknown`

### `objective_relationship`

允许值：

- `core_family`
- `relative_family`
- `in_law`
- `coworker_or_former_coworker`
- `classmate_or_alumni`
- `service_or_practical_collaboration`
- `friend`
- `mentioned_indirect`
- `other`
- `unknown`

### `identity_confidence`

允许值：

- `locked`
- `high`
- `medium`
- `low`
- `do_not_merge`

### `call_name_confidence`

允许值：

- `locked`
- `strong`
- `candidate`
- `unsafe`
- `unknown`

### `communication_profile`（已废弃）

该字段不再承载具体说话风格。关系节点只保存 `dyadic_profile_ref`，指向 `runtime/dyadic-profiles` 中的对象级画像。

原因：同一种客观关系内部，不同人的话题、节奏、主动性和表达机制差异很大。按关系类型维护一套风格会生成机械模板。

旧结构仅作为迁移参考：

```text
CommunicationProfile
  tone
  directness
  humor_level
  message_density
  initiative_level
  usual_topics[]
  avoid_topics[]
  sensitive_contexts[]
  opener_patterns[]
  response_patterns[]
```

建议枚举：

- `tone`: `warm`, `direct`, `analytical`, `playful`, `formal`, `careful`
- `directness`: `low`, `medium`, `high`
- `humor_level`: `none`, `light`, `medium`, `high`
- `message_density`: `short`, `medium`, `dense`
- `initiative_level`: `rare`, `occasional`, `frequent`, `unknown`

### `permission_profile`

```text
PermissionProfile
  can_retrieve_context
  can_generate_draft
  can_proactively_suggest
  can_auto_send
  requires_user_approval
  approval_reasons[]
```

默认值：

- 直接微信关系：可检索、可生成草稿、可建议主动沟通、不可自动发送、需要确认
- 间接提及人物：可检索上下文、不可主动、不可自动发送、需要确认

## RelationshipEdge

```text
RelationshipEdge
  edge_id
  source_person_id
  target_person_id
  edge_type
  weight
  evidence_type
  evidence_refs[]
  risk_notes[]
```

### `edge_type`

允许值：

- `self_to_person`
- `person_mentioned_with_person`
- `same_group`
- `family_relation`
- `coworker_relation`
- `classmate_relation`
- `service_relation`
- `topic_relation`
- `alias_relation`

## AliasRecord

```text
AliasRecord
  alias
  person_id
  canonical_name
  alias_type
  confidence
  evidence_refs[]
  notes
```

### `alias_type`

允许值：

- `wechat_name`
- `call_name`
- `group_name`
- `old_name`
- `mentioned_alias`
- `candidate`

## EvidenceRef

```text
EvidenceRef
  source_file
  source_type
  local_id
  episode_id
  evidence_kind
  confidence
  redaction_level
```

### `evidence_kind`

允许值：

- `user_confirmed`
- `direct_call`
- `at_mention`
- `quoted_reply`
- `self_introduction`
- `stable_group_name`
- `co_occurrence`
- `topic_inference`
- `manual_override`
- `candidate_only`

## Audit

```text
Audit
  total_people
  direct_count
  mentioned_count
  call_evidence_count
  call_name_equals_wechat_name_count
  risky_merge_count
  unresolved_alias_count
  generated_at
```

## Update Policy

### 快速更新

- 高频主题
- 主要场景
- 最近互动
- 主动沟通建议分

### 需要多次证据

- 沟通语气
- 主动频率
- 关系定位
- 兴趣圈层

### 必须用户确认

- 亲密关系和家庭关系
- 身份合并
- 真实姓名映射
- 自动发送权限
- 高风险称呼修正
