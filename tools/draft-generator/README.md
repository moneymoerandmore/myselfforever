# 最小草稿生成器

这个工具用于验证数字分身的第一条运行闭环：

输入联系人 + 场景 + 意图，输出：

- 草稿
- 关系依据
- 话题依据
- 语气依据
- 风险等级
- 是否需要用户确认

它是本地规则版，不调用外部模型。

## 使用

```powershell
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\draft-generator\draft_generator.py `
  --query "联系人或称呼" `
  --scenario "对方发来的消息或你想主动聊的场景" `
  --intent work_discussion
```

可选意图：

- `casual_chat`
- `work_discussion`
- `decision_request`
- `emotional_support`
- `family_coordination`
- `investment_discussion`
- `news_discussion`
- `logistics`
- `conflict`
- `unknown`

输出 JSON：

```powershell
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\draft-generator\draft_generator.py `
  --query "联系人或称呼" `
  --scenario "场景" `
  --intent news_discussion `
  --format json
```

## 数据源

默认读取：

`C:\Users\cloud\Documents\Codex\2026-06-09\new-chat\outputs\relationship_dimensions.csv`

可以通过 `--csv` 指定其他关系维度表。

## 当前限制

- 这是规则版草稿，不是最终自然语言模型。
- 只读取关系 CSV，不读取完整聊天上下文。
- 自动发送禁用。
- 对称呼证据保守处理：没有强证据时不会强行在草稿里使用称呼。

## 批量评估

运行 30 条可执行评估：

```powershell
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\draft-generator\eval_runner.py
```

写入报告：

```powershell
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\draft-generator\eval_runner.py `
  --output evals\results\draft-generator-eval.md
```
