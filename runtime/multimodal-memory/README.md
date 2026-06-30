# Multimodal Memory

This directory stores user-confirmed features extracted from multimodal intake.

- `confirmed-features.jsonl` is append-only runtime memory.
- Each line is confirmed by the user from the multimodal intake page.
- These records are read by dashboard prompts as evidence, but they do not directly rewrite `SelfCore.v0.1.md`.
