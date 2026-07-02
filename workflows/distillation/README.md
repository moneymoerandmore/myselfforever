# 个人 Skill 蒸馏工作流

## 目标

把外部微信清洗产物转成可审计、可回放、可继续蒸馏的个人 skill 语料入口。

当前优先级：

1. 蒸馏前语料抽查
2. 三观骨架提炼
3. 思维模型和决策启发式提炼
4. 表达 DNA 提炼
5. 边界/反模式提炼
6. 最终生成个人 skill

## 输入

默认读取外部产物目录：

```text
C:\Users\cloud\Documents\Codex\2026-06-03\skill\outputs
```

关键文件：

- `wechat-distill-core-episodes.jsonl`
- `wechat-distill-style-episodes.jsonl`
- `wechat-distill-counterexample-episodes.jsonl`
- `wechat-distill-background-episodes.jsonl`
- `wechat-distill-stratification-manifest.json`
- `wechat-distill-stratification-review.md`

## 输出

- `reports/pre-distillation-corpus-audit.md`

报告只保留 episode ID、分数、标签和源文件哈希，不把聊天正文复制进仓库。

## 命令

```powershell
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" workflows\distillation\scripts\audit_wechat_distill_corpus.py
```

可指定输入和输出：

```powershell
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" workflows\distillation\scripts\audit_wechat_distill_corpus.py `
  --outputs-dir "C:\Users\cloud\Documents\Codex\2026-06-03\skill\outputs" `
  --report "workflows\distillation\reports\pre-distillation-corpus-audit.md"
```

## 解读原则

- `core` 优先从 `three_views` 高的 episode 开始读，再看 `thinking`。
- `style` 只用于表达机制，不机械模仿口癖、私密称呼或一次性情绪。
- `counter` 用来补边界、误判、过度用力和不应自动发送的场景。
- `copylike_or_long_burst` 与 `very_large_burst` 需要人工回看，避免把复制、转发或 AI 式长文当成真实表达。
- `background_high_three_views` 如果出现，优先人工判断是否应升入 core。
