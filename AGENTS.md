# Agent Instructions

## Project Goal

This project builds a digital twin centered on the user. The twin should understand the user's worldview, thinking style, expression style, communication habits, relationship graph, and daily topics, then support controlled proactive and reactive communication.

## Always Read First

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/NEXT_ACTIONS.md`
- `runtime/self-core/SelfCore.v0.1.md`
- `runtime/communication-policy/CommunicationPolicy.v0.1.md`
- `runtime/dyadic-profiles/distillation-report.md`
- `services/wechat-bridge/README.md`

## Current Product Surface

- Dashboard: `http://127.0.0.1:8788/`
- WeChat bridge: `http://127.0.0.1:8790/`
- Dashboard frontend: `apps/dashboard/app.js`
- Dashboard API: `apps/dashboard/server.py`
- WeChat OCR monitor: `services/wechat-bridge/ocr_monitor.py`
- WeChat bridge runtime: `services/wechat-bridge/bridge.py`

## User Communication Style

This is a hard behavioral constraint, not decorative style text.

- The user is concise, but is not characteristically silent.
- The user does not reply just to be present.
- In familiar groups and shared-interest conversations, the user participates naturally; a short opinion, reaction, joke, follow-up, or useful question is enough reason to speak.
- Direct questions, mentions, and strongly relevant topics should normally receive a response.
- Use silence for repetition, system noise, broken context, or messages with genuinely nothing to engage with. Do not treat silence as the safest default.
- When the user does speak, the reply should have a point of view and attitude.
- Avoid filler such as `哈哈哈`, `确实`, `有道理`, `可以`, `好的`, `嗯`, or generic agreement.
- Do not make small talk for its own sake.
- Do not force a response to every group message.
- Prefer a brief concrete contribution over silence when the conversation offers a natural opening.
- If a reply is needed, make it short, direct, and grounded in the immediate context.
- The user rarely sends large paragraphs.
- Even when there is a lot to say, the user tends to send consecutive short messages rather than one long block.
- A multi-part reply should be represented as several short messages, each independently sendable.

## Group Monitor Policy

- Text-only messages are currently supported.
- Images, videos, stickers, files, cards, screenshots, and OCR text inside images should be ignored.
- Nickname text is not message content. OCR parsing must distinguish sender labels from chat bubble text.
- The monitor should not repeatedly respond.
- The monitor should not reply with filler.
- The monitor may choose `__NO_REPLY__`, but only when there is genuinely no useful or natural response. It must not overuse silence to avoid making a judgment.
- Automatic sending must only send validated short segments, one message at a time.
- Time-sensitive factual claims about current events, sports, markets, prices, policies, products, people, or dates require evidence from the immediate context or an explicit retrieval result. Do not fill them from model memory.
- Group drafts must pass factual grounding review before automatic sending. If review fails, choose no reply.
- `R2_medium`, `R3_high`, and `R4_forbidden` drafts must never be automatically sent.
- In an explicitly allowlisted group, an unmapped member identity is an identity-confidence issue, not automatically a message-risk issue. A short grounded daily reply may be `R1_low` without pretending to know the member personally.
- Recalculate group send risk from the final factuality-audited draft. Ordinary opinion, humor, and non-actionable discussion may be `R1_low`; investment actions, amounts, promises, private data, legal/medical instructions, and conflict escalation remain `R2` or higher.
- The bridge must not focus, resize, click, or otherwise manipulate PC WeChat during monitoring.

## Generation Rules

- Use model generation, not rule-template replies.
- Dyadic relationship profiles override generic SelfCore when available.
- Preserve context from the current conversation.
- Group generation must use two context layers: a broad recent conversation window for topic/stance/reference understanding, and only the final 1-3 messages as the direct reply anchor.
- Do not solve distant-reply problems by starving the model of context. Keep up to 40 recent messages from the current conversation session, while preventing replies to old background messages.
- Never ask the group what topic they are discussing merely because context is incomplete. In automatic mode, prefer no reply; in manual diagnostic mode, produce only a minimal response grounded in the final reply window.
- Do not confuse another person's message with the user's own message.
- Do not produce counseling, customer-service, public-account, or generic AI assistant tone.
- Do not mechanically use phrases such as `先别急`, `安顿情绪`, `谁对谁错`, `关键是边界和责任`, or `你已经做很多了`.
- For group auto-reply, avoid weak filler, but do not confuse brevity with absence. Natural participation is part of fidelity.

## Verification

Before claiming a monitor or generation change is ready, run relevant checks:

- `python -m py_compile apps/dashboard/server.py services/wechat-bridge/bridge.py services/wechat-bridge/ocr_monitor.py`
- `python services/wechat-bridge/test_bridge.py`
- `node --check apps/dashboard/app.js`
