# 项目路线图

完整架构见 [数字分身项目架构](ARCHITECTURE.md)。

当前项目采用“数字我五层架构”：

1. 本我层：`SelfCore`，沉淀三观、判断方式、表达 DNA、边界和身份事实。
2. 表我层：`RelationshipGraph`、`DyadicProfile`、`CommunicationPolicy`，沉淀不同人眼里的我、亲密度、共同话题、表达风格和权限。
3. 现实信息输入层：微信聊天记录、多模态材料、关系线索、外部事件，生成证据和候选。
4. 真我-数字我持续对齐层：每日新闻、观点校对、回复纠错、关系修正，反馈到本我和表我。
5. 对外交互层：群聊被动回复、主动发起话题、草稿、辅助发送和低风险自动发送。

## 阶段 0：项目真相源

目标：把已有对话成果收束成可持续推进的项目。

状态：已完成初版。

- 已建立项目 README
- 已建立迁入对话索引
- 已建立数据边界说明
- 已建立工作流目录说明
- 已建立主架构文档

## 阶段 1：本我初始化

目标：先让系统能回答“我会怎么看”，并把三观、判断方式、表达 DNA、边界和身份事实沉淀到 `SelfCore`。

待做：

- 生成 `SelfCore v0.1`：已完成初稿，见 `runtime/self-core/SelfCore.v0.1.md`
- 定义 `SelfCore` schema：已完成初稿，见 `runtime/self-core/schema.md`
- 定义身份事实子模块：已建立 `runtime/self-core/identity-facts/`，用于承载“我会什么 / 不会什么 / 偏好 / 生活约束 / 禁止自称”等稳定本我事实。
- 建立 30-50 条评估用例：已完成 30 条初稿，见 `evals/cases/selfcore-v0.1.md`
- 下一步：用每日新闻对齐和不像我反馈继续生成 SelfCore 候选，而不是直接改写本我。
- 下一步：从历史聊天记录和持续交互反馈中抽取 `IdentityFactCandidate`，经确认后进入 `runtime/self-core/identity-facts/facts.jsonl`。

## 阶段 2：表我初始化

目标：把社会关系、亲密度、共同话题、表达风格和权限边界整理成可运行的表我。

待做：

- 把关系链图谱整理成可检索的 `RelationshipGraph v0.1`：已完成运行模型初稿，见 `runtime/relationship-graph/RelationshipGraph.v0.1.md`
- 定义人物、关系、共同话题、称呼证据 schema：已完成初稿，见 `runtime/relationship-graph/schema.md`
- 双人表现型：已完成首轮聚合蒸馏，见 `runtime/dyadic-profiles/profiles.json`
- 设计 `CommunicationPolicy v0.1`：已完成初稿，见 `runtime/communication-policy/CommunicationPolicy.v0.1.md`
- 下一步：明确每个重要关系的亲密度、表达原则、可主动沟通权限和自动发送边界。

## 阶段 3：现实输入与候选池

目标：让微信聊天记录和多模态材料持续变成证据、候选和可审计更新。

待做：

- 微信聊天记录导入、清洗、episode 抽取：已有原始数据和部分派生成果，仍需固化流水线。
- 多模态摄入页面：已完成独立页，见 `apps/dashboard/multimodal.html`
- SelfCore 候选池：已完成候选确认、合并和注入工作台，见 `apps/dashboard/selfcore-candidates.html`
- 下一步：把多模态候选明确分流到本我候选、表我候选和策略候选。

## 阶段 4：真我-数字我持续对齐

目标：用具体新闻、回复纠错和关系校对持续细化三观、判断和表达边界。

待做：

- 新闻对齐页面：已完成初版，见 `apps/dashboard/news-alignment.html`
- 建立每日校对流程
- 记录我的观点确认、纠错和反例
- 生成更新提案
- 慢变量更新必须经过我确认

## 阶段 5：对外交互层

目标：让数字我逐步参与现实生活中的主动和被动沟通。

待做：

- 支持输入某人消息，生成回复草稿：已完成本地规则版，见 `tools/draft-generator/draft_generator.py`
- 支持输入联系人，生成主动沟通草稿：已完成本地规则版，见 `tools/draft-generator/draft_generator.py`
- 每条草稿显示依据：关系、话题、语气、风险
- 把我的选择和改写记录成反馈
- 群聊被动回复：已接入 PC 微信旁路服务和 Dashboard
- 事实审计、双层上下文、风险重算：已接入群聊自动回复链路
- 下一步：把“像我/不像我/我会这样改”作为反馈入口，分别更新本我和表我。

## 阶段 6：本地 dashboard 整合

目标：把本我、表我、现实输入、真我对齐和对外交互放到统一入口。

待做：

- 首页：今日状态、待校对事项、候选主动沟通、最近风险拦截
- 草稿页：已完成本地 v0.1，见 `apps/dashboard/`
- 关系页：人物、关系、共同话题、最近互动
- 生成时优先加载联系人 `DyadicProfile`：已接入 dashboard Poe prompt
- 下一步：从对应私聊中检索少量脱敏同场景 episode，作为 few-shot 风格证据
- 下一步：增加“像我/不像我/我会这样改”联系人级反馈，优先更新该联系人的画像
- 分身页：SelfCore、表达 DNA、边界、版本历史
- 新闻页：每日新闻、我的可能观点、可聊对象
- 审计页：证据、风险、更新记录

## 阶段 7：受控半自动沟通

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
