# Dyadic Distiller

从本地微信原始 JSON 中蒸馏“我面对具体联系人时的沟通表现型”。

```powershell
& "C:\Users\cloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" `
  tools\dyadic-distiller\distill_dyadic_profiles.py
```

默认输出：

- `runtime/dyadic-profiles/profiles.json`
- `runtime/dyadic-profiles/distillation-report.md`

隐私规则：只输出聚合统计和机制标签，不输出原始聊天正文。

