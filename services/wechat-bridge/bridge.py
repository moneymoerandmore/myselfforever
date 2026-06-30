"""Core state and policy for the local WeChat sidecar service."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
from typing import Any
from urllib import request
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_event_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None


def recent_group_context(
    events: list["GroupEvent"] | list[dict[str, Any]],
    max_messages: int = 40,
    max_span_seconds: int = 60 * 60,
    max_gap_seconds: int = 15 * 60,
) -> list[dict[str, Any]]:
    rendered = [asdict(item) if isinstance(item, GroupEvent) else dict(item) for item in events]
    if not rendered:
        return []

    deduped: list[dict[str, Any]] = []
    for item in rendered:
        if deduped:
            previous = deduped[-1]
            previous_time = parse_event_time(previous.get("occurred_at", ""))
            current_time = parse_event_time(item.get("occurred_at", ""))
            seconds = (
                (current_time - previous_time).total_seconds()
                if previous_time and current_time
                else None
            )
            if (
                item.get("sender") == previous.get("sender")
                and item.get("content") == previous.get("content")
                and seconds is not None
                and 0 <= seconds <= 60
            ):
                continue
        deduped.append(item)

    latest_time = parse_event_time(deduped[-1].get("occurred_at", ""))
    selected = [deduped[-1]]
    newer_time = latest_time
    for item in reversed(deduped[:-1]):
        if len(selected) >= max_messages:
            break
        item_time = parse_event_time(item.get("occurred_at", ""))
        if latest_time and item_time and (latest_time - item_time).total_seconds() > max_span_seconds:
            break
        if newer_time and item_time and (newer_time - item_time).total_seconds() > max_gap_seconds:
            break
        selected.append(item)
        newer_time = item_time
    selected.reverse()
    return selected


@dataclass
class GroupEvent:
    group: str
    sender: str
    content: str
    occurred_at: str = field(default_factory=now_iso)
    source: str = "manual"
    event_id: str = ""

    def __post_init__(self) -> None:
        self.group = self.group.strip()
        self.sender = self.sender.strip()
        self.content = self.content.strip()
        if not self.event_id:
            material = f"{self.group}\n{self.sender}\n{self.content}\n{self.occurred_at}"
            self.event_id = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


@dataclass
class ReviewItem:
    review_id: str
    status: str
    created_at: str
    trigger_event_id: str
    group: str
    sender: str
    trigger_reasons: list[str]
    context: list[dict[str, Any]]
    draft: str = ""
    draft_metadata: dict[str, Any] = field(default_factory=dict)
    decision_note: str = ""


class JsonlStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = root / "events.jsonl"
        self.reviews_path = root / "reviews.json"
        self._lock = threading.RLock()

    def append_event(self, event: GroupEvent) -> None:
        with self._lock, self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    def save_reviews(self, reviews: list[ReviewItem]) -> None:
        with self._lock:
            payload = [asdict(item) for item in reviews]
            self.reviews_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_events(self) -> list[GroupEvent]:
        if not self.events_path.exists():
            return []
        events = []
        with self._lock, self.events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                    events.append(GroupEvent(**payload))
                except (TypeError, json.JSONDecodeError):
                    continue
        return events

    def load_reviews(self) -> list[ReviewItem]:
        if not self.reviews_path.exists():
            return []
        try:
            payload = json.loads(self.reviews_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        reviews = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                reviews.append(ReviewItem(**item))
            except TypeError:
                continue
        return reviews


class BridgeRuntime:
    def __init__(self, data_root: Path) -> None:
        self.store = JsonlStore(data_root)
        self.running = False
        self.groups: set[str] = set()
        self.self_names: set[str] = set()
        self.keywords: set[str] = set()
        self.adapter = "manual"
        self.dashboard_url = "http://127.0.0.1:8788"
        self.context_limit = 80
        self.poe_api_key = ""
        self.poe_model = "Claude-Sonnet-4"
        self.trigger_all = False
        self.auto_reply = False
        self.auto_send_replies = False
        self.reply_settle_seconds = 10
        self.reply_cooldown_seconds = 90
        self.contexts: dict[str, list[GroupEvent]] = {}
        self.event_ids: set[str] = set()
        self.reviews: list[ReviewItem] = []
        self._lock = threading.RLock()
        self.load_state()

    def load_state(self) -> None:
        for event in self.store.load_events():
            self.event_ids.add(event.event_id)
            context = self.contexts.setdefault(event.group, [])
            context.append(event)
            del context[:-self.context_limit]
        self.reviews = self.store.load_reviews()

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        groups = {str(item).strip() for item in payload.get("groups") or [] if str(item).strip()}
        self_names = {str(item).strip() for item in payload.get("self_names") or [] if str(item).strip()}
        if not groups:
            raise ValueError("groups is required")
        if not self_names:
            raise ValueError("self_names is required")
        adapter = str(payload.get("adapter") or "manual").strip()
        if adapter not in {"manual", "uia_probe", "window_capture_ocr"}:
            raise ValueError("invalid adapter")
        with self._lock:
            self.groups = groups
            self.self_names = self_names
            self.keywords = {
                str(item).strip().lower() for item in payload.get("keywords") or [] if str(item).strip()
            }
            self.adapter = adapter
            self.dashboard_url = str(payload.get("dashboard_url") or self.dashboard_url).rstrip("/")
            self.context_limit = max(10, min(int(payload.get("context_limit") or 80), 200))
            self.trigger_all = bool(payload.get("trigger_all", False))
            self.auto_reply = bool(payload.get("auto_reply", False))
            self.auto_send_replies = bool(payload.get("auto_send", False))
            if self.auto_send_replies:
                self.auto_reply = True
            self.reply_settle_seconds = max(3, min(int(payload.get("reply_settle_seconds") or 10), 60))
            self.reply_cooldown_seconds = max(15, min(int(payload.get("reply_cooldown_seconds") or 90), 600))
            if payload.get("poe_api_key"):
                self.poe_api_key = str(payload["poe_api_key"]).strip()
            if payload.get("poe_model"):
                self.poe_model = str(payload["poe_model"]).strip()
            self.running = True
        return self.status()

    def stop(self) -> dict[str, Any]:
        self.running = False
        return self.status()

    def status(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "groups": sorted(self.groups),
            "self_names": sorted(self.self_names),
            "keywords": sorted(self.keywords),
            "adapter": self.adapter,
            "context_limit": self.context_limit,
            "event_count": len(self.event_ids),
            "review_count": len(self.reviews),
            "pending_review_count": sum(item.status in {"pending", "drafted"} for item in self.reviews),
            "auto_send": self.auto_send_replies,
            "trigger_all": self.trigger_all,
            "model_ready": bool(self.poe_api_key),
            "auto_reply": self.auto_reply,
            "reply_settle_seconds": self.reply_settle_seconds,
            "reply_cooldown_seconds": self.reply_cooldown_seconds,
        }

    def trigger_reasons(self, event: GroupEvent) -> list[str]:
        if event.sender in self.self_names:
            return []
        lowered = event.content.lower()
        reasons = []
        if self.trigger_all:
            reasons.append("active_group_mode")
        if any(f"@{name.lower()}" in lowered for name in self.self_names):
            reasons.append("mentioned_self")
        if any(keyword in lowered for keyword in self.keywords):
            reasons.append("keyword")
        if reasons and event.content.rstrip().endswith(("?", "？")):
            reasons.append("question")
        return reasons

    def configure_model(self, payload: dict[str, Any]) -> dict[str, Any]:
        api_key = str(payload.get("poe_api_key") or "").strip()
        if not api_key:
            raise ValueError("poe_api_key is required")
        self.poe_api_key = api_key
        self.poe_model = str(payload.get("poe_model") or self.poe_model).strip()
        return self.status()

    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.running:
            raise ValueError("watcher is not running")
        event = GroupEvent(
            group=str(payload.get("group") or ""),
            sender=str(payload.get("sender") or ""),
            content=str(payload.get("content") or ""),
            occurred_at=str(payload.get("occurred_at") or now_iso()),
            source=str(payload.get("source") or self.adapter),
            event_id=str(payload.get("event_id") or ""),
        )
        if not event.group or not event.sender or not event.content:
            raise ValueError("group, sender and content are required")
        if event.group not in self.groups:
            raise ValueError("group is not in the watch allowlist")
        with self._lock:
            if event.event_id in self.event_ids:
                return {"duplicate": True, "event": asdict(event), "review": None}
            previous = self.contexts.get(event.group, [])[-1:] or []
            if previous and event.source == "window_capture_ocr":
                previous_event = previous[0]
                previous_time = parse_event_time(previous_event.occurred_at)
                event_time = parse_event_time(event.occurred_at)
                seconds = (
                    (event_time - previous_time).total_seconds()
                    if previous_time and event_time
                    else None
                )
                if (
                    previous_event.sender == event.sender
                    and previous_event.content == event.content
                    and seconds is not None
                    and 0 <= seconds <= 20
                ):
                    return {"duplicate": True, "event": asdict(event), "review": None}
            self.event_ids.add(event.event_id)
            context = self.contexts.setdefault(event.group, [])
            context.append(event)
            del context[:-self.context_limit]
            self.store.append_event(event)
            suppress_review = bool(payload.get("suppress_review", False))
            reasons = [] if suppress_review else self.trigger_reasons(event)
            review = None
            if reasons:
                review = ReviewItem(
                    review_id=uuid4().hex,
                    status="pending",
                    created_at=now_iso(),
                    trigger_event_id=event.event_id,
                    group=event.group,
                    sender=event.sender,
                    trigger_reasons=reasons,
                    context=recent_group_context(context),
                )
                self.reviews.insert(0, review)
                self.store.save_reviews(self.reviews)
        return {
            "duplicate": False,
            "event": asdict(event),
            "trigger_reasons": reasons,
            "review": asdict(review) if review else None,
        }

    def events(self, group: str = "") -> list[dict[str, Any]]:
        if group:
            return [asdict(item) for item in self.contexts.get(group, [])]
        return [asdict(item) for name in sorted(self.contexts) for item in self.contexts[name]]

    def generate_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        review_id = str(payload.get("review_id") or "")
        review = next((item for item in self.reviews if item.review_id == review_id), None)
        if review is None:
            raise ValueError("review not found")
        api_key = str(payload.get("poe_api_key") or self.poe_api_key or "").strip()
        if not api_key:
            raise ValueError("poe_api_key is required")
        review_context = recent_group_context(review.context)
        history = [
            {
                "role": "self" if item["sender"] in self.self_names else "contact",
                "content": f"[{item['sender']}] {item['content']}",
            }
            for item in review_context
        ]
        request_payload = {
            "query": review.sender,
            "scenario": review_context[-1]["content"],
            "conversation_history": history,
            "poe_api_key": api_key,
            "poe_model": str(payload.get("poe_model") or self.poe_model),
            "intent": str(payload.get("intent") or "unknown"),
            "mode": "draft",
            "allow_no_reply": True,
            "response_policy": "active_group",
            "factuality_guard": True,
            "trusted_group": True,
        }
        body = json.dumps(request_payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            f"{self.dashboard_url}/api/draft",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            raise ValueError(result.get("error") or "dashboard draft failed")
        generated = result["result"]
        draft_segments = [
            str(item).strip()
            for item in generated.get("draft_segments") or []
            if str(item).strip()
        ]
        review.draft = str(generated.get("draft_text") or "")
        review.draft_metadata = {
            "risk_level": generated.get("risk_level"),
            "tone_basis": generated.get("tone_basis"),
            "relationship_basis": generated.get("relationship_basis"),
            "topic_basis": generated.get("topic_basis"),
            "draft_segments": draft_segments,
            "no_reply": bool(generated.get("no_reply", False)),
            "factuality_status": generated.get("factuality_status"),
            "factuality_reason": generated.get("factuality_reason"),
        }
        review.status = "skipped_no_reply" if generated.get("no_reply") or not review.draft else "drafted"
        self.store.save_reviews(self.reviews)
        return asdict(review)

    def decide_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        review_id = str(payload.get("review_id") or "")
        decision = str(payload.get("decision") or "")
        if decision not in {"approved_for_manual_send", "rejected"}:
            raise ValueError("invalid decision")
        review = next((item for item in self.reviews if item.review_id == review_id), None)
        if review is None:
            raise ValueError("review not found")
        review.status = decision
        review.decision_note = str(payload.get("note") or "")
        self.store.save_reviews(self.reviews)
        return asdict(review)
