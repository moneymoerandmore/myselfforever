# 项目路线图

完整架构见 [数字分身项目架构](ARCHITECTURE.md)。

## 阶段 0：项目真相源

目标：把已有对话成果收束成可持续推进的项目。

状态：已完成初版。

- 已建立项目 README
- 已建立迁入对话索引
- 已建立数据边界说明
- 已建立工作流目录说明
- 已建立主架构文档

## 阶段 1：只读数字分身

目标：先让系统能回答“我会怎么看、我和谁是什么关系、我和 TA 常聊什么”。

待做：

- 生成 `SelfCore v0.1`：已完成初稿，见 `runtime/self-core/SelfCore.v0.1.md`
- 定义 `SelfCore` schema：已完成初稿，见 `runtime/self-core/schema.md`
- 把关系链图谱整理成可检索的 `RelationshipGraph v0.1`：已完成运行模型初稿，见 `runtime/relationship-graph/RelationshipGraph.v0.1.md`
- 定义人物、关系、共同话题、称呼证据 schema：已完成初稿，见 `runtime/relationship-graph/schema.md`
- 建立 30-50 条评估用例：已完成 30 条初稿，见 `evals/cases/selfcore-v0.1.md`

## 阶段 2：草稿型数字分身

目标：能生成像我的回复和主动开场，但默认不自动发送。

待做：

- 设计 `CommunicationPolicy v0.1`：已完成初稿，见 `runtime/communication-policy/CommunicationPolicy.v0.1.md`
- 支持输入某人消息，生成回复草稿：已完成本地规则版，见 `tools/draft-generator/draft_generator.py`
- 支持输入联系人，生成主动沟通草稿：已完成本地规则版，见 `tools/draft-generator/draft_generator.py`
- 每条草稿显示依据：关系、话题、语气、风险
- 把我的选择和改写记录成反馈

## 阶段 3：每日校对与新闻讨论

目标：让数字分身开始受控自进化。

待做：

- 建立每日校对流程
- 建立新闻讨论流程
- 记录我的观点确认、纠错和反例
- 生成更新提案
- 慢变量更新必须经过我确认

## 阶段 4：本地 dashboard

目标：把“我、关系、主动沟通、每日校对”放到一个本地入口。

待做：

- 首页：今日状态、待校对事项、候选主动沟通
- 草稿页：已完成本地 v0.1，见 `apps/dashboard/`
- 关系页：人物、关系、共同话题、最近互动
- 双人表现型：已完成首轮聚合蒸馏，见 `runtime/dyadic-profiles/profiles.json`
- 生成时优先加载联系人 `DyadicProfile`：已接入 dashboard Poe prompt
- 下一步：从对应私聊中检索少量脱敏同场景 episode，作为 few-shot 风格证据
- 下一步：增加“像我/不像我/我会这样改”联系人级反馈，优先更新该联系人的画像
- 分身页：SelfCore、表达 DNA、边界、版本历史
- 新闻页：每日新闻、我的可能观点、可聊对象
- 审计页：证据、风险、更新记录

## 阶段 5：受控半自动沟通

目标：在低风险、已授权场景下，让数字分身有限自动化。

待做：

- 联系人级权限
- 场景级权限
- 自动发送白名单
- 高风险内容强制回到我确认
- 全量日志、停用和回滚机制

### PC 微信伴随服务

- 架构与数据边界：已纳入 `docs/ARCHITECTURE.md`
- 第一阶段旁路服务：已建立 `services/wechat-bridge/`
- 每群独立多轮上下文、消息去重、触发判断和待审队列：已完成初版
- 与 Dashboard/Poe 草稿接口衔接：已完成初版
- 新版 PC 微信 UI Automation 控件探测：进行中
- 自动发送：保持禁用，待旁路模式稳定后再进入确认发送阶段

## 当前最应该做的下一步

1. 校对 `SelfCore v0.1`，标记“不像我”和“过度概括”的地方。
2. 校对 `RelationshipGraph v0.1`，尤其是称呼证据和主动沟通边界。
3. 校对 `CommunicationPolicy v0.1`，确认主动时间、风险等级和自动发送边界。
4. 用最小草稿生成器跑 30 条评估用例，验证“像不像我”“认不认得人”和“会不会越界”：已建立 runner，见 `tools/draft-generator/eval_runner.py`
5. 将 dashboard 草稿页接入更多联系人审计和历史上下文。
