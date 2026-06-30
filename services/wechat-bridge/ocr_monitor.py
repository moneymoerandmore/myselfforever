"""Polling OCR monitor for one allowlisted personal Weixin group."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import threading
import time
from typing import Any

from PIL import Image
from rapidocr_onnxruntime import RapidOCR

from window_capture import capture_weixin_offscreen
from wechat_controller import send_to_focused_input


BLOCKED_AUTO_REPLY_TERMS = {
    "买入", "卖出", "加仓", "减仓", "仓位", "收益", "止损", "目标价", "金额",
    "转账", "密码", "验证码", "保证", "承诺", "内幕", "吵架", "隐私",
}

NON_TEXT_MESSAGE_MARKERS = {
    "[图片]", "[视频]", "[动画表情]", "[表情]", "[文件]", "[语音]", "[链接]", "[小程序]",
    "图片", "视频", "动画表情", "表情包", "语音", "文件", "拍了拍", "撤回了一条消息",
}

CARD_TEXT_MARKERS = {
    "AppKey", "BUVID", "详情地址", "问题反馈", "问题描述", "问题分类", "创建人",
    "http://", "https://", "www.", "UID", "截图", "附件",
}

AUTO_SEND_RISK_LEVELS = {"R0_safe", "R1_low"}
AUTO_SEND_FACTUALITY_STATUSES = {"passed", "rewritten"}


def auto_send_block_reason(metadata: dict[str, Any]) -> str:
    risk_level = str(metadata.get("risk_level") or "")
    if risk_level not in AUTO_SEND_RISK_LEVELS:
        return "blocked_risk"
    factuality_status = str(metadata.get("factuality_status") or "")
    if factuality_status not in AUTO_SEND_FACTUALITY_STATUSES:
        return "blocked_factuality"
    return ""


def looks_like_text_message(content: str) -> bool:
    text = content.strip()
    if not text:
        return False
    if len(text) > 90:
        return False
    if any(marker in text for marker in NON_TEXT_MESSAGE_MARKERS):
        return False
    if any(marker in text for marker in CARD_TEXT_MARKERS):
        return False
    if re.fullmatch(r"[\W_]+", text):
        return False
    if re.fullmatch(r"\d{1,2}:\d{2}", text):
        return False
    return True


def _brightness(rgb: tuple[int, int, int]) -> float:
    return sum(rgb) / 3


def _line_background_stats(image: Image.Image, line: dict[str, Any]) -> dict[str, float]:
    x = int(line["x"])
    y = int(line["y"])
    width = int(line["width"])
    height = int(line["height"])
    samples = []
    for yy in range(max(0, y - 8), min(image.height, y + height + 8), 3):
        for xx in range(max(0, x - 12), min(image.width, x + width + 12), 3):
            samples.append(image.getpixel((xx, yy))[:3])
    if not samples:
        return {"dark_bubble_ratio": 0.0, "white_ratio": 0.0, "median_brightness": 0.0}
    brightness_values = sorted(_brightness(pixel) for pixel in samples)
    median_brightness = brightness_values[len(brightness_values) // 2]
    dark_bubble_count = sum(
        38 <= pixel[0] <= 75 and 38 <= pixel[1] <= 75 and 38 <= pixel[2] <= 75 for pixel in samples
    )
    white_count = sum(_brightness(pixel) > 180 for pixel in samples)
    return {
        "dark_bubble_ratio": dark_bubble_count / len(samples),
        "white_ratio": white_count / len(samples),
        "median_brightness": median_brightness,
    }


def is_message_bubble_line(line: dict[str, Any]) -> bool:
    stats = line.get("background") or {}
    return (
        float(stats.get("dark_bubble_ratio") or 0) >= 0.35
        and float(stats.get("white_ratio") or 0) <= 0.35
        and float(stats.get("median_brightness") or 0) >= 36
    )


def is_sender_label_line(line: dict[str, Any], region_width: int) -> bool:
    text = str(line.get("text") or "").strip()
    stats = line.get("background") or {}
    if not (1 <= len(text) <= 24):
        return False
    if float(line.get("x") or 0) > region_width * 0.38:
        return False
    if is_message_bubble_line(line):
        return False
    if float(stats.get("white_ratio") or 0) > 0.25:
        return False
    if re.fullmatch(r"\d{1,2}:\d{2}", text):
        return False
    if any(mark in text for mark in "：:？！?。，"):
        return False
    return True


def extract_messages_from_ocr_lines(lines: list[dict[str, Any]], region_width: int) -> list[dict[str, str]]:
    messages = []
    lines = sorted(lines, key=lambda item: (item["y"], item["x"]))
    senders = [line for line in lines if is_sender_label_line(line, region_width)]
    for line in lines:
        content = str(line.get("text") or "").strip()
        if not is_message_bubble_line(line):
            continue
        if not looks_like_text_message(content):
            continue
        if float(line.get("width") or 0) > region_width * 0.55:
            continue
        candidates = [
            sender
            for sender in senders
            if 12 <= float(line["y"]) - float(sender["y"]) <= 82
            and abs(float(line["x"]) - float(sender["x"])) <= region_width * 0.12
        ]
        if not candidates:
            continue
        sender = max(candidates, key=lambda item: item["y"])
        material = f"{sender['text']}\n{content}\n{round(float(line['y']) / 4)}"
        fingerprint = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
        messages.append({"sender": str(sender["text"]), "content": content, "fingerprint": fingerprint})
    return messages


def message_key(message: dict[str, str]) -> tuple[str, str]:
    sender = re.sub(r"\s+", " ", str(message.get("sender") or "")).strip()
    content = re.sub(r"\s+", " ", str(message.get("content") or "")).strip()
    return sender, content


def new_messages_since_previous(
    previous: list[dict[str, str]], current: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Return only messages appended after the previous visible OCR frame."""
    if not previous or not current:
        return []
    previous_keys = [message_key(item) for item in previous]
    current_keys = [message_key(item) for item in current]
    if previous_keys == current_keys:
        return []
    max_overlap = min(len(previous_keys), len(current_keys))
    for overlap in range(max_overlap, 0, -1):
        if previous_keys[-overlap:] == current_keys[:overlap]:
            return current[overlap:]
    return []


class OcrMonitor:
    def __init__(self, runtime: Any, data_root: Path) -> None:
        self.runtime = runtime
        self.data_root = data_root
        self.engine = RapidOCR()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.previous_snapshot: list[dict[str, str]] = []
        self.last_error = ""
        self.last_scan_at = ""
        self.last_message_count = 0
        self.pending_messages: list[dict[str, str]] = []
        self.pending_first_seen = 0.0
        self.pending_last_seen = 0.0
        self.last_reply_at = 0.0

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.previous_snapshot = []
        self.thread = threading.Thread(target=self.run, name="wechat-ocr-monitor", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive() and threading.current_thread() is not self.thread:
            self.thread.join(timeout=2.0)
        if self.thread and not self.thread.is_alive():
            self.thread = None

    def status(self) -> dict[str, Any]:
        return {
            "running": bool(self.thread and self.thread.is_alive() and not self.stop_event.is_set()),
            "last_error": self.last_error,
            "last_scan_at": self.last_scan_at,
            "last_message_count": self.last_message_count,
            "pending_message_count": len(self.pending_messages),
            "cooldown_remaining_seconds": max(
                0,
                int(self.runtime.reply_cooldown_seconds - (time.time() - self.last_reply_at)),
            ),
        }

    def run(self) -> None:
        initialized = False
        while not self.stop_event.wait(4.0):
            if not self.runtime.running or self.runtime.adapter != "window_capture_ocr":
                continue
            try:
                messages = self.scan()
                self.last_scan_at = time.strftime("%Y-%m-%d %H:%M:%S")
                self.last_message_count = len(messages)
                if not initialized:
                    self.previous_snapshot = messages
                    initialized = True
                    continue
                new_messages = new_messages_since_previous(self.previous_snapshot, messages)
                self.previous_snapshot = messages
                for message in new_messages:
                    self.queue_message(message)
                self.flush_pending_if_ready()
                self.last_error = ""
            except Exception as exc:
                self.last_error = str(exc)

    def queue_message(self, message: dict[str, str]) -> None:
        now = time.time()
        message = dict(message)
        material = f"{message.get('sender', '')}\n{message.get('content', '')}\n{time.time_ns()}"
        message["event_id"] = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
        if not self.pending_messages:
            self.pending_first_seen = now
        self.pending_last_seen = now
        self.pending_messages.append(message)
        del self.pending_messages[:-8]

    def flush_pending_if_ready(self) -> None:
        if not self.pending_messages:
            return
        now = time.time()
        if now - self.pending_last_seen < self.runtime.reply_settle_seconds:
            return
        should_reply = self.runtime.auto_reply and self.runtime.poe_api_key
        in_cooldown = now - self.last_reply_at < self.runtime.reply_cooldown_seconds
        pending = self.pending_messages
        self.pending_messages = []
        self.pending_first_seen = 0.0
        self.pending_last_seen = 0.0
        group = next(iter(self.runtime.groups))
        last_result = None
        for index, message in enumerate(pending):
            last_result = self.runtime.ingest(
                {
                    "group": group,
                    "sender": message["sender"],
                    "content": message["content"],
                    "source": "window_capture_ocr",
                    "event_id": message.get("event_id") or message["fingerprint"],
                    "suppress_review": index < len(pending) - 1,
                }
            )
        review = (last_result or {}).get("review")
        if review and should_reply and not in_cooldown:
            self.handle_review(review)
            self.last_reply_at = time.time()

    def scan(self) -> list[dict[str, str]]:
        screenshot = self.data_root / "latest-window.png"
        capture_weixin_offscreen(screenshot)
        image = Image.open(screenshot)
        width, height = image.size
        region = image.crop((int(width * 0.27), int(height * 0.11), width, height))
        result, _ = self.engine(region)
        lines = []
        for box, text, score in result or []:
            if score < 0.72:
                continue
            x = min(point[0] for point in box)
            y = min(point[1] for point in box)
            width_value = max(point[0] for point in box) - x
            height_value = max(point[1] for point in box) - y
            lines.append(
                {
                    "x": x,
                    "y": y,
                    "width": width_value,
                    "height": height_value,
                    "text": text.strip(),
                }
            )
        region = region.convert("RGB")
        for line in lines:
            line["background"] = _line_background_stats(region, line)
        messages = extract_messages_from_ocr_lines(lines, region.width)
        return messages[-12:]

    def handle_review(self, review: dict[str, Any]) -> None:
        source_text = "\n".join(item["content"] for item in review["context"][-6:])
        if any(term in source_text for term in BLOCKED_AUTO_REPLY_TERMS):
            return
        generated = self.runtime.generate_review(
            {"review_id": review["review_id"], "intent": "casual_chat"}
        )
        draft = generated.get("draft") or ""
        item = next(item for item in self.runtime.reviews if item.review_id == review["review_id"])
        segments = [
            str(segment).strip()
            for segment in item.draft_metadata.get("draft_segments", [])
            if str(segment).strip()
        ] or [part.strip() for part in draft.splitlines() if part.strip()]
        segments = segments[:5]
        if not segments:
            item.status = "skipped_no_reply"
            self.runtime.store.save_reviews(self.runtime.reviews)
            return
        if any(term in "\n".join(segments) for term in BLOCKED_AUTO_REPLY_TERMS):
            return
        if self.runtime.auto_send_replies:
            blocked_status = auto_send_block_reason(item.draft_metadata)
            if blocked_status:
                item.status = blocked_status
                self.runtime.store.save_reviews(self.runtime.reviews)
                return
            for segment in segments:
                send_to_focused_input(segment, commit=True)
                time.sleep(0.8)
            item.status = "sent_by_group_monitor"
        else:
            item.status = "drafted_by_group_monitor"
        self.runtime.store.save_reviews(self.runtime.reviews)
