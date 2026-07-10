# Identity Facts

`identity-facts` is a SelfCore submodule.

It stores stable facts about the real user that constrain what the digital self may claim, promise, prefer, or do. These facts are part of the inner-self layer, not the raw input layer.

## Boundary

- `facts.jsonl`: confirmed identity facts that can be used at runtime.
- `corrections.jsonl`: explicit user corrections with highest priority.
- `candidates.jsonl`: extracted but unconfirmed candidates from chat logs, multimodal intake, and interaction feedback.
- `schema.json`: the record contract.

Reality inputs such as chat logs and multimodal material can produce candidates, but they do not become identity facts until confirmed or strongly supported by repeated evidence.

## Runtime Rule

Generation must load relevant identity facts before producing a reply. If a draft conflicts with a high-confidence identity fact, the runtime must rewrite, downgrade, or block it.
