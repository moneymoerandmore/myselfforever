#!/usr/bin/env python

from pathlib import Path
from tempfile import TemporaryDirectory
import time

from bridge import BridgeRuntime, recent_group_context
from ocr_monitor import (
    OcrMonitor,
    auto_send_block_reason,
    extract_messages_from_ocr_lines,
    looks_like_text_message,
    new_messages_since_previous,
)


def main() -> int:
    with TemporaryDirectory() as directory:
        runtime = BridgeRuntime(Path(directory))
        runtime.start(
            {
                "groups": ["项目群"],
                "self_names": ["我"],
                "keywords": ["AI"],
            }
        )
        quiet = runtime.ingest({"group": "项目群", "sender": "张三", "content": "今天进展正常"})
        assert quiet["review"] is None
        unrelated_question = runtime.ingest(
            {"group": "项目群", "sender": "王五", "content": "你们中午吃什么？"}
        )
        assert unrelated_question["review"] is None
        triggered = runtime.ingest(
            {"group": "项目群", "sender": "李四", "content": "@我 这个 AI 方案你怎么看？"}
        )
        assert set(triggered["trigger_reasons"]) == {"mentioned_self", "keyword", "question"}
        assert len(runtime.events("项目群")) == 3
        assert len(runtime.reviews[0].context) == 3
        assert runtime.status()["auto_send"] is False
        assert looks_like_text_message("该买小米了？")
        assert not looks_like_text_message("[图片]")
        assert not looks_like_text_message("AppKey: android64 / 8860410")
        assert not looks_like_text_message("https://example.com/a/b")
        parsed = extract_messages_from_ocr_lines(
            [
                {
                    "x": 101,
                    "y": 51,
                    "width": 132,
                    "height": 26,
                    "text": "暂时不碰汽车股",
                    "background": {"dark_bubble_ratio": 0.03, "white_ratio": 0.0, "median_brightness": 30.3},
                },
                {
                    "x": 117,
                    "y": 95,
                    "width": 72,
                    "height": 32,
                    "text": "怕什么",
                    "background": {"dark_bubble_ratio": 0.90, "white_ratio": 0.08, "median_brightness": 47.3},
                },
                {
                    "x": 165,
                    "y": 310,
                    "width": 101,
                    "height": 20,
                    "text": "暂时不碰汽车股",
                    "background": {"dark_bubble_ratio": 0.0, "white_ratio": 1.0, "median_brightness": 250.0},
                },
                {
                    "x": 177,
                    "y": 342,
                    "width": 57,
                    "height": 25,
                    "text": "怕什么",
                    "background": {"dark_bubble_ratio": 0.01, "white_ratio": 0.90, "median_brightness": 237.7},
                },
                {
                    "x": 101,
                    "y": 417,
                    "width": 178,
                    "height": 26,
                    "text": "LAXY-明 智驾长草期",
                    "background": {"dark_bubble_ratio": 0.09, "white_ratio": 0.0, "median_brightness": 30.3},
                },
                {
                    "x": 117,
                    "y": 460,
                    "width": 155,
                    "height": 29,
                    "text": "我必将逐帧记录",
                    "background": {"dark_bubble_ratio": 0.87, "white_ratio": 0.11, "median_brightness": 47.3},
                },
                {
                    "x": 103,
                    "y": 651,
                    "width": 91,
                    "height": 21,
                    "text": "看好bilibili",
                    "background": {"dark_bubble_ratio": 0.02, "white_ratio": 0.0, "median_brightness": 30.3},
                },
                {
                    "x": 133,
                    "y": 845,
                    "width": 140,
                    "height": 29,
                    "text": "这得好好学学",
                    "background": {"dark_bubble_ratio": 0.04, "white_ratio": 0.70, "median_brightness": 240.0},
                },
            ],
            1257,
        )
        assert [item["content"] for item in parsed] == ["怕什么", "我必将逐帧记录"]
        assert [item["sender"] for item in parsed] == ["暂时不碰汽车股", "LAXY-明 智驾长草期"]
        stable_frame = [{"sender": "张三", "content": "同一句", "fingerprint": "old-y"}]
        shifted_frame = [{"sender": "张三", "content": "同一句", "fingerprint": "new-y"}]
        assert new_messages_since_previous(stable_frame, shifted_frame) == []
        appended_frame = shifted_frame + [{"sender": "李四", "content": "新一句", "fingerprint": "m2"}]
        assert [item["content"] for item in new_messages_since_previous(shifted_frame, appended_frame)] == [
            "新一句"
        ]
        replaced_frame = [{"sender": "王五", "content": "无重叠画面", "fingerprint": "m3"}]
        assert new_messages_since_previous(appended_frame, replaced_frame) == []
        assert auto_send_block_reason(
            {"risk_level": "R3_high", "factuality_status": "passed"}
        ) == "blocked_risk"
        assert auto_send_block_reason(
            {"risk_level": "R1_low", "factuality_status": "audit_failed"}
        ) == "blocked_factuality"
        assert auto_send_block_reason(
            {"risk_level": "R1_low", "factuality_status": "rewritten"}
        ) == ""

        trimmed = recent_group_context(
            [
                {"sender": "甲", "content": "旧话题", "occurred_at": "2026-06-12T09:40:00+08:00"},
                {"sender": "乙", "content": "新话题", "occurred_at": "2026-06-12T10:05:00+08:00"},
                {"sender": "乙", "content": "新话题", "occurred_at": "2026-06-12T10:05:10+08:00"},
                {"sender": "丙", "content": "接着聊", "occurred_at": "2026-06-12T10:05:20+08:00"},
            ]
        )
        assert [item["content"] for item in trimmed] == ["新话题", "接着聊"]

        throttle_runtime = BridgeRuntime(Path(directory) / "throttle")
        throttle_runtime.start(
            {
                "groups": ["项目群"],
                "self_names": ["我"],
                "trigger_all": True,
                "auto_reply": False,
                "reply_settle_seconds": 3,
                "reply_cooldown_seconds": 15,
            }
        )
        monitor = OcrMonitor(throttle_runtime, Path(directory) / "throttle")
        monitor.queue_message({"sender": "张三", "content": "第一句", "fingerprint": "m1"})
        monitor.queue_message({"sender": "张三", "content": "第二句", "fingerprint": "m2"})
        monitor.flush_pending_if_ready()
        assert len(throttle_runtime.events("项目群")) == 0
        monitor.pending_last_seen = time.time() - 4
        monitor.flush_pending_if_ready()
        assert len(throttle_runtime.events("项目群")) == 2
        assert len(throttle_runtime.reviews) == 1
        duplicate = throttle_runtime.ingest(
            {
                "group": "项目群",
                "sender": "张三",
                "content": "第二句",
                "source": "window_capture_ocr",
                "event_id": "m2-shifted",
            }
        )
        assert duplicate["duplicate"] is True
        assert len(throttle_runtime.events("项目群")) == 2
    print("wechat bridge tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
