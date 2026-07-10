# CommunicationPolicy v0.1

## 版本信息

- 版本：`CommunicationPolicy v0.1`
- 生成时间：2026-06-10
- 拆分时间：2026-07-02
- 依赖：`SelfCore v0.1`, `RelationshipGraph v0.1`
- 原始来源：微信日常说话习惯分析、每日主动话题触发池、一周主动交流执行计划

## 定位

`CommunicationPolicy` 原本同时承载两类不同工作：

1. 数字“我”对外沟通：什么时候主动说话、对谁说、怎么回复、什么风险必须拦截。
2. 数字“我”和用户本人对齐：每日新闻讨论、观点校对、纠错、形成 `SelfCore` 更新提案。

这两类工作共享 `SelfCore` 和表达风格，但架构边界不同。前者是运行时沟通策略，后者是自我蒸馏与版本化更新策略。为避免后续实现混线，v0.1 拆为两个子策略文件：

- [OutboundCommunicationPolicy.v0.1.md](OutboundCommunicationPolicy.v0.1.md)：对外主动/被动沟通、风险门控、草稿/发送边界。
- [../self-alignment/NewsAlignmentPolicy.v0.1.md](../self-alignment/NewsAlignmentPolicy.v0.1.md)：每日新闻讨论、和我的校对、`Correction` / `PreferenceSignal` / `UpdateProposal` 等自进化输入。

在新的“数字我”架构里，`CommunicationPolicy` 的对外部分属于表我层。它不只是“怎么说话”的规则，而是规定本我如何在不同社会关系中外显：

- 对不同人，亲密度、默认背景、玩笑强度、直接程度、回复速度和主动频率都不同。
- 对不同群，参与阈值、上下文容量、事实审计和自动发送边界都不同。
- 对未映射成员，可以低风险接日常话，但不能使用私人称呼、关系假设或高亲密度表达。
- `SelfCore` 里的身份事实高于表我层。社会关系和双人画像只能调整外显方式，不能覆盖用户会什么、不会什么、真实偏好、生活约束或禁止承诺。
- 每次真我纠正“这不像我”时，要判断它是在修正本我，还是修正某段关系中的表我。

## 当前实现映射

- 对外草稿生成：`apps/dashboard/server.py` 的 `/api/draft`
- 群聊旁路与风险审计：`services/wechat-bridge/`
- SelfCore 候选池：`runtime/multimodal-memory/confirmed-features.jsonl`
- 候选合并与注入：`apps/dashboard/server.py` 的 `/api/selfcore-candidates/*`
- 候选工作台：`apps/dashboard/selfcore-candidates.html`

## 后续实现原则

- 对外沟通策略不得直接改写 `SelfCore`。
- 新闻对齐策略不得直接自动对外发送。
- 每日新闻讨论产生的是可审计候选、校对记录和更新提案，不是立即生效的人格改写。
- 慢变量进入 `SelfCore` 前必须经过用户确认、合并、备份和注入日志。
