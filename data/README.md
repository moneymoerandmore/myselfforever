# 数据说明

本目录用于记录数据来源、schema、脱敏样本和生成物说明。

当前不保存原始微信聊天记录，也不保存全量派生 JSONL。原因：

- 原始聊天记录包含高敏感隐私。
- 已有派生文件体积很大，不适合直接纳入仓库。
- 项目前期更需要稳定 schema、流程和小样本测试。

## 本机现有数据源

- 原始聊天导出：`C:\tmp\wechat-raw`
- 蒸馏语料输出：`C:\Users\cloud\Documents\Codex\2026-06-03\skill\outputs`
- 关系链图谱输出：`C:\Users\cloud\Documents\Codex\2026-06-09\new-chat\outputs`
- 主动聊天分析输出：`C:\Users\cloud\Documents\Codex\2026-06-08\new-chat\outputs`

## 后续可迁入内容

- schema 文档
- 字段说明
- 小规模脱敏样本
- 构建命令和校验命令
- 数据质量审计报告

## 不应迁入内容

- 未脱敏原始聊天记录
- 真实姓名映射表
- 家庭、公司、亲密关系细节的明文长表
- 全量 JSONL 派生语料
