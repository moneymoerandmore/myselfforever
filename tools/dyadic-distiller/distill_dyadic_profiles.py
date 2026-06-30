#!/usr/bin/env python
"""Distill person-specific communication profiles from local WeChat exports.

The output is aggregate-only: no raw message text or reconstructable dialogue is
written into the repository.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import csv
import hashlib
import json
import re
from pathlib import Path
from statistics import median
from typing import Any


DEFAULT_RAW_DIR = Path(r"C:\tmp\wechat-raw")
DEFAULT_RELATIONSHIP_DIR = Path(
    r"C:\Users\cloud\Documents\Codex\2026-06-09\new-chat\outputs"
)
SELF_NAMES = {"方方", "在路上", "Cloudfang"}
THREAD_GAP_SECONDS = 6 * 60 * 60
BURST_GAP_SECONDS = 120

TOPICS = {
    "ai_technology": ["ai", "模型", "大模型", "算法", "代码", "产品", "互联网", "token", "智能"],
    "work_organization": ["工作", "公司", "老板", "同事", "组织", "项目", "目标", "业务", "部门", "汇报"],
    "investment_market": ["股票", "投资", "基金", "市场", "买入", "卖出", "仓位", "涨", "跌", "美股"],
    "family_parenting": ["孩子", "宝宝", "女儿", "儿子", "爸", "妈", "家庭", "幼儿园", "老人"],
    "housing_city": ["房子", "买房", "装修", "小区", "上海", "南京", "房价", "贷款"],
    "food_social": ["吃饭", "饭", "喝酒", "聚餐", "餐厅", "约饭", "请客"],
    "games_entertainment": ["游戏", "war3", "魔兽", "电影", "视频", "b站", "直播"],
    "health_medical": ["医院", "医生", "药", "身体", "健康", "手术", "检查", "睡觉"],
    "travel_life": ["旅游", "旅行", "日本", "美国", "酒店", "机票", "宠物", "猫"],
    "relationship_emotion": ["焦虑", "生气", "吵", "情绪", "难受", "关系", "责任", "边界"],
}

TOPIC_LABELS = {
    "ai_technology": "AI与技术",
    "work_organization": "工作与组织",
    "investment_market": "投资与市场",
    "family_parenting": "家庭与育儿",
    "housing_city": "住房与城市",
    "food_social": "吃饭与社交",
    "games_entertainment": "游戏与娱乐",
    "health_medical": "健康与医疗",
    "travel_life": "旅行与生活",
    "relationship_emotion": "关系与情绪",
}

MARKERS = {
    "question": ["?", "？", "怎么", "咋", "啥", "为什么", "为啥", "是不是", "真的吗", "真的假的"],
    "judgment": ["我觉得", "我感觉", "本质", "关键", "问题是", "明显", "肯定", "不对", "确实"],
    "boundary": ["不要", "不需要", "不能", "不可能", "别", "不该", "没必要"],
    "action": ["先", "今天", "明天", "回头", "我来", "确认", "推进", "安排", "处理"],
    "uncertainty": ["可能", "也许", "感觉", "不一定", "先看看", "再说", "我猜"],
    "laughter": ["哈哈", "hh", "笑死", "[捂脸]", "[偷笑]", "[呲牙]"],
    "strong_reaction": ["卧槽", "离谱", "牛逼", "神经病", "太惨", "这也行"],
    "acknowledgement": ["好", "嗯", "可以", "收到", "行", "ok", "好的"],
}

QUOTE_RE = re.compile(r"\[引用\s+([^：:\]]+)[：:]", re.IGNORECASE)
AT_RE = re.compile(r"@([^\s@，,。！？!?：:]+)")
BRACKET_RE = re.compile(r"\[[^\]]{1,12}\]")
URL_RE = re.compile(r"https?://|\[链接\]|\[图片\]|\[视频\]")


def split_alias_field(value: str) -> list[str]:
    aliases: list[str] = []
    for item in re.split(r"[；;]", value or ""):
        item = item.strip()
        if not item:
            continue
        aliases.append(item.rsplit(":", 1)[0].strip())
    return aliases


def normalize_alias(value: str) -> str:
    return "".join(
        char.lower()
        for char in (value or "").strip().lstrip("@").strip()
        if char.isalnum() or "\u4e00" <= char <= "\u9fff"
    )


def load_aliases(relationship_dir: Path) -> tuple[dict[str, str], dict[str, set[str]]]:
    alias_to_person: dict[str, str] = {}
    person_aliases: dict[str, set[str]] = defaultdict(set)

    alias_json_path = relationship_dir / "identity_alias_map.json"
    if alias_json_path.exists():
        payload = json.loads(alias_json_path.read_text(encoding="utf-8"))
        for alias, canonical in (payload.get("aliases") or {}).items():
            alias = str(alias or "").strip()
            canonical = str(canonical or "").strip()
            if not alias or not canonical:
                continue
            alias_to_person[normalize_alias(alias)] = canonical
            person_aliases[canonical].add(alias)
            person_aliases[canonical].add(canonical)

    alias_path = relationship_dir / "identity_alias_map.csv"
    if alias_path.exists():
        with alias_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                canonical = (row.get("统一身份") or "").strip()
                if not canonical:
                    continue
                aliases = [canonical]
                aliases.extend(split_alias_field(row.get("用户名/wxid") or ""))
                aliases.extend(split_alias_field(row.get("姓名/昵称/群昵称") or ""))
                for alias in aliases:
                    if alias:
                        alias_to_person.setdefault(normalize_alias(alias), canonical)
                        person_aliases[canonical].add(alias)

    dimensions_path = relationship_dir / "relationship_dimensions.csv"
    if dimensions_path.exists():
        with dimensions_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                canonical = (row.get("人物") or row.get("展示名称") or "").strip()
                if not canonical:
                    continue
                for key in ("人物", "称呼名", "微信名"):
                    for alias in re.split(r"\s*/\s*", (row.get(key) or "").strip()):
                        if alias:
                            alias_to_person.setdefault(normalize_alias(alias), canonical)
                            person_aliases[canonical].add(alias)
    return alias_to_person, person_aliases


def canonicalize(name: str, alias_to_person: dict[str, str]) -> str:
    cleaned = (name or "").strip().lstrip("@").strip()
    if not cleaned:
        return ""
    return alias_to_person.get(normalize_alias(cleaned), cleaned)


def clean_content(content: Any) -> str:
    text = str(content or "").strip()
    text = re.sub(r"\[引用\s+.*$", "", text, flags=re.DOTALL).strip()
    return text


def parse_time(message: dict[str, Any]) -> datetime | None:
    value = message.get("formattedTime")
    if value:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    timestamp = message.get("createTime")
    try:
        return datetime.fromtimestamp(int(timestamp))
    except (TypeError, ValueError, OSError):
        return None


def marker_hits(text: str, markers: list[str]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def topic_hits(text: str) -> set[str]:
    lowered = text.lower()
    return {
        topic
        for topic, terms in TOPICS.items()
        if any(term.lower() in lowered for term in terms)
    }


@dataclass
class ProfileAccumulator:
    canonical_name: str
    aliases: set[str] = field(default_factory=set)
    source_files: set[str] = field(default_factory=set)
    shared_groups: set[str] = field(default_factory=set)
    private_sessions: set[str] = field(default_factory=set)
    private_outgoing_count: int = 0
    private_incoming_count: int = 0
    group_directed_outgoing_count: int = 0
    group_directed_incoming_count: int = 0
    outgoing_texts: list[str] = field(default_factory=list)
    incoming_texts: list[str] = field(default_factory=list)
    outgoing_times: list[datetime] = field(default_factory=list)
    incoming_times: list[datetime] = field(default_factory=list)
    all_events: list[tuple[datetime, str]] = field(default_factory=list)
    outgoing_topics: Counter[str] = field(default_factory=Counter)
    incoming_topics: Counter[str] = field(default_factory=Counter)
    marker_counts: Counter[str] = field(default_factory=Counter)
    media_response_count: int = 0

    def add_message(self, text: str, when: datetime | None, direction: str, evidence: str) -> None:
        if direction == "outgoing":
            if evidence == "private_direct":
                self.private_outgoing_count += 1
            else:
                self.group_directed_outgoing_count += 1
            if text:
                self.outgoing_texts.append(text)
                for topic in topic_hits(text):
                    self.outgoing_topics[topic] += 1
                for marker, terms in MARKERS.items():
                    if marker_hits(text, terms):
                        self.marker_counts[marker] += 1
                if URL_RE.search(text):
                    self.media_response_count += 1
            if when:
                self.outgoing_times.append(when)
                self.all_events.append((when, "outgoing"))
        else:
            if evidence == "private_direct":
                self.private_incoming_count += 1
            else:
                self.group_directed_incoming_count += 1
            if text:
                self.incoming_texts.append(text)
                for topic in topic_hits(text):
                    self.incoming_topics[topic] += 1
            if when:
                self.incoming_times.append(when)
                self.all_events.append((when, "incoming"))


def extract_target(content: str) -> str:
    quote = QUOTE_RE.search(content or "")
    if quote:
        return quote.group(1).strip()
    at_match = AT_RE.search(content or "")
    if at_match:
        return at_match.group(1).strip()
    return ""


def process_private(
    path: Path,
    data: dict[str, Any],
    alias_to_person: dict[str, str],
    profiles: dict[str, ProfileAccumulator],
) -> None:
    session = data.get("session") or {}
    raw_name = session.get("displayName") or session.get("nickname") or path.stem.removeprefix("私聊_")
    canonical = canonicalize(str(raw_name), alias_to_person)
    profile = profiles.setdefault(canonical, ProfileAccumulator(canonical))
    profile.aliases.add(str(raw_name))
    profile.private_sessions.add(str(raw_name))
    profile.source_files.add(path.name)

    for message in data.get("messages") or []:
        direction = "outgoing" if int(message.get("isSend") or 0) == 1 else "incoming"
        profile.add_message(
            clean_content(message.get("content")),
            parse_time(message),
            direction,
            "private_direct",
        )


def process_group(
    path: Path,
    data: dict[str, Any],
    alias_to_person: dict[str, str],
    profiles: dict[str, ProfileAccumulator],
) -> None:
    session = data.get("session") or {}
    group_name = str(session.get("displayName") or session.get("nickname") or path.stem)
    for message in data.get("messages") or []:
        content = str(message.get("content") or "")
        target_raw = extract_target(content)
        sender_raw = str(message.get("senderDisplayName") or "")
        is_send = int(message.get("isSend") or 0) == 1
        when = parse_time(message)

        if is_send and target_raw:
            canonical = canonicalize(target_raw, alias_to_person)
            if canonical and canonical not in SELF_NAMES:
                profile = profiles.setdefault(canonical, ProfileAccumulator(canonical))
                profile.aliases.add(target_raw)
                profile.shared_groups.add(group_name)
                profile.source_files.add(path.name)
                profile.add_message(clean_content(content), when, "outgoing", "group_directed")
        elif not is_send and target_raw and canonicalize(target_raw, alias_to_person) in SELF_NAMES:
            canonical = canonicalize(sender_raw, alias_to_person)
            if canonical:
                profile = profiles.setdefault(canonical, ProfileAccumulator(canonical))
                profile.aliases.add(sender_raw)
                profile.shared_groups.add(group_name)
                profile.source_files.add(path.name)
                profile.add_message(clean_content(content), when, "incoming", "group_directed")


def safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) / denominator, 4) if denominator else 0.0


def calculate_threads(events: list[tuple[datetime, str]]) -> tuple[float, int, int]:
    ordered = sorted(events)
    outgoing_starts = 0
    incoming_starts = 0
    previous_time: datetime | None = None
    for when, direction in ordered:
        if previous_time is None or (when - previous_time).total_seconds() >= THREAD_GAP_SECONDS:
            if direction == "outgoing":
                outgoing_starts += 1
            else:
                incoming_starts += 1
        previous_time = when
    total = outgoing_starts + incoming_starts
    return safe_ratio(outgoing_starts, total), outgoing_starts, incoming_starts


def calculate_reply_latency(events: list[tuple[datetime, str]]) -> float | None:
    ordered = sorted(events)
    latencies: list[float] = []
    previous: tuple[datetime, str] | None = None
    for current in ordered:
        if previous and previous[1] == "incoming" and current[1] == "outgoing":
            seconds = (current[0] - previous[0]).total_seconds()
            if 0 <= seconds <= 24 * 60 * 60:
                latencies.append(seconds)
        previous = current
    return round(median(latencies), 1) if latencies else None


def calculate_bursts(events: list[tuple[datetime, str]]) -> tuple[float, int, float]:
    ordered = sorted(events)
    bursts: list[int] = []
    current = 0
    previous_time: datetime | None = None
    previous_direction = ""
    for when, direction in ordered:
        same_burst = (
            direction == "outgoing"
            and previous_direction == "outgoing"
            and previous_time is not None
            and (when - previous_time).total_seconds() <= BURST_GAP_SECONDS
        )
        if direction == "outgoing":
            if same_burst:
                current += 1
            else:
                if current:
                    bursts.append(current)
                current = 1
        elif current:
            bursts.append(current)
            current = 0
        previous_time = when
        previous_direction = direction
    if current:
        bursts.append(current)
    if not bursts:
        return 0.0, 0, 0.0
    return round(sum(bursts) / len(bursts), 2), max(bursts), safe_ratio(sum(1 for x in bursts if x > 1), len(bursts))


def dominant_mechanisms(marker_counts: Counter[str], total: int) -> list[dict[str, Any]]:
    items = []
    for name, count in marker_counts.most_common():
        items.append({"mechanism": name, "count": count, "ratio": safe_ratio(count, total)})
    return items[:6]


def confidence(profile: ProfileAccumulator) -> dict[str, Any]:
    private_total = profile.private_outgoing_count + profile.private_incoming_count
    directed_total = profile.group_directed_outgoing_count + profile.group_directed_incoming_count
    weighted = private_total + directed_total * 0.55
    if private_total >= 500 or weighted >= 1200:
        level = "high"
    elif private_total >= 100 or weighted >= 250:
        level = "medium"
    elif weighted >= 30:
        level = "low"
    else:
        level = "insufficient"
    limitations = []
    if not profile.private_sessions:
        limitations.append("没有私聊样本，画像主要来自群聊定向互动。")
    if directed_total < 20 and not profile.private_sessions:
        limitations.append("定向样本过少，不应直接用于高拟真生成。")
    return {
        "level": level,
        "score": round(min(1.0, weighted / 1200), 4),
        "weighted_sample_count": round(weighted, 1),
        "limitations": limitations,
    }


def build_profile(profile: ProfileAccumulator, known_aliases: set[str]) -> dict[str, Any]:
    outgoing_total = profile.private_outgoing_count + profile.group_directed_outgoing_count
    incoming_total = profile.private_incoming_count + profile.group_directed_incoming_count
    text_lengths = [len(text) for text in profile.outgoing_texts if text]
    initiation_ratio, outgoing_starts, incoming_starts = calculate_threads(profile.all_events)
    average_burst, max_burst, multi_burst_ratio = calculate_bursts(profile.all_events)
    all_topics = profile.outgoing_topics + profile.incoming_topics
    shared_topics = [
        {
            "topic": topic,
            "label": TOPIC_LABELS.get(topic, topic),
            "total_count": count,
            "my_count": profile.outgoing_topics.get(topic, 0),
            "their_count": profile.incoming_topics.get(topic, 0),
        }
        for topic, count in all_topics.most_common(10)
    ]
    hour_counts = Counter(when.hour for when in profile.outgoing_times)
    daypart_counts = {
        "morning_06_11": sum(hour_counts[h] for h in range(6, 12)),
        "noon_12_13": sum(hour_counts[h] for h in range(12, 14)),
        "afternoon_14_17": sum(hour_counts[h] for h in range(14, 18)),
        "evening_18_21": sum(hour_counts[h] for h in range(18, 22)),
        "late_night_22_05": sum(hour_counts[h] for h in list(range(22, 24)) + list(range(0, 6))),
    }
    weekday_count = sum(1 for when in profile.outgoing_times if when.weekday() < 5)
    first_time = min((when for when, _ in profile.all_events), default=None)
    last_time = max((when for when, _ in profile.all_events), default=None)

    return {
        "profile_id": "dyad_" + hashlib.sha256(profile.canonical_name.encode("utf-8")).hexdigest()[:12],
        "person_key": profile.canonical_name,
        "canonical_name": profile.canonical_name,
        "aliases": sorted(profile.aliases | known_aliases),
        "evidence": {
            "private_session_count": len(profile.private_sessions),
            "private_outgoing_count": profile.private_outgoing_count,
            "private_incoming_count": profile.private_incoming_count,
            "group_directed_outgoing_count": profile.group_directed_outgoing_count,
            "group_directed_incoming_count": profile.group_directed_incoming_count,
            "shared_group_count": len(profile.shared_groups),
            "shared_groups": sorted(profile.shared_groups),
            "first_interaction_at": first_time.isoformat(sep=" ") if first_time else None,
            "last_interaction_at": last_time.isoformat(sep=" ") if last_time else None,
            "source_files": sorted(profile.source_files),
        },
        "topics": {
            "shared_topics": shared_topics,
            "my_outgoing_topics": dict(profile.outgoing_topics.most_common(10)),
            "their_incoming_topics": dict(profile.incoming_topics.most_common(10)),
            "topic_diversity": len(all_topics),
        },
        "interaction_pattern": {
            "initiation_ratio": initiation_ratio,
            "outgoing_thread_starts": outgoing_starts,
            "incoming_thread_starts": incoming_starts,
            "median_reply_seconds": calculate_reply_latency(profile.all_events),
            "average_burst_size": average_burst,
            "max_burst_size": max_burst,
            "multi_message_burst_ratio": multi_burst_ratio,
            "outgoing_incoming_ratio": safe_ratio(outgoing_total, incoming_total),
        },
        "expression_pattern": {
            "outgoing_text_count": len(profile.outgoing_texts),
            "average_chars": round(sum(text_lengths) / len(text_lengths), 2) if text_lengths else 0.0,
            "median_chars": round(float(median(text_lengths)), 2) if text_lengths else 0.0,
            "short_message_ratio": safe_ratio(sum(1 for length in text_lengths if length <= 10), len(text_lengths)),
            "question_marker_ratio": safe_ratio(profile.marker_counts["question"], len(profile.outgoing_texts)),
            "exclamation_ratio": safe_ratio(sum("!" in x or "！" in x for x in profile.outgoing_texts), len(profile.outgoing_texts)),
            "laughter_ratio": safe_ratio(profile.marker_counts["laughter"], len(profile.outgoing_texts)),
            "emoji_or_bracket_ratio": safe_ratio(sum(bool(BRACKET_RE.search(x)) for x in profile.outgoing_texts), len(profile.outgoing_texts)),
            "judgment_marker_ratio": safe_ratio(profile.marker_counts["judgment"], len(profile.outgoing_texts)),
            "boundary_marker_ratio": safe_ratio(profile.marker_counts["boundary"], len(profile.outgoing_texts)),
            "action_marker_ratio": safe_ratio(profile.marker_counts["action"], len(profile.outgoing_texts)),
            "uncertainty_marker_ratio": safe_ratio(profile.marker_counts["uncertainty"], len(profile.outgoing_texts)),
            "strong_reaction_ratio": safe_ratio(profile.marker_counts["strong_reaction"], len(profile.outgoing_texts)),
            "acknowledgement_ratio": safe_ratio(profile.marker_counts["acknowledgement"], len(profile.outgoing_texts)),
            "dominant_mechanisms": dominant_mechanisms(profile.marker_counts, len(profile.outgoing_texts)),
        },
        "temporal_pattern": {
            "hour_distribution": {str(hour): count for hour, count in sorted(hour_counts.items())},
            "daypart_distribution": daypart_counts,
            "weekday_ratio": safe_ratio(weekday_count, len(profile.outgoing_times)),
            "weekend_ratio": safe_ratio(len(profile.outgoing_times) - weekday_count, len(profile.outgoing_times)),
        },
        "channel_pattern": {
            "private_ratio": safe_ratio(profile.private_outgoing_count, outgoing_total),
            "group_directed_ratio": safe_ratio(profile.group_directed_outgoing_count, outgoing_total),
        },
        "confidence": confidence(profile),
    }


def merge_accumulators(profiles: dict[str, ProfileAccumulator]) -> ProfileAccumulator:
    merged = ProfileAccumulator("__global__")
    for name, profile in profiles.items():
        if name in SELF_NAMES:
            continue
        merged.private_outgoing_count += profile.private_outgoing_count
        merged.private_incoming_count += profile.private_incoming_count
        merged.group_directed_outgoing_count += profile.group_directed_outgoing_count
        merged.group_directed_incoming_count += profile.group_directed_incoming_count
        merged.outgoing_texts.extend(profile.outgoing_texts)
        merged.incoming_texts.extend(profile.incoming_texts)
        merged.outgoing_times.extend(profile.outgoing_times)
        merged.incoming_times.extend(profile.incoming_times)
        merged.all_events.extend(profile.all_events)
        merged.outgoing_topics.update(profile.outgoing_topics)
        merged.incoming_topics.update(profile.incoming_topics)
        merged.marker_counts.update(profile.marker_counts)
    return merged


def add_global_contrast(profile: dict[str, Any], global_profile: dict[str, Any]) -> None:
    expression = profile["expression_pattern"]
    global_expression = global_profile["expression_pattern"]
    comparisons = {
        "average_chars": expression["average_chars"] - global_expression["average_chars"],
        "short_message_ratio": expression["short_message_ratio"] - global_expression["short_message_ratio"],
        "question_marker_ratio": expression["question_marker_ratio"] - global_expression["question_marker_ratio"],
        "judgment_marker_ratio": expression["judgment_marker_ratio"] - global_expression["judgment_marker_ratio"],
        "boundary_marker_ratio": expression["boundary_marker_ratio"] - global_expression["boundary_marker_ratio"],
        "action_marker_ratio": expression["action_marker_ratio"] - global_expression["action_marker_ratio"],
        "laughter_ratio": expression["laughter_ratio"] - global_expression["laughter_ratio"],
        "strong_reaction_ratio": expression["strong_reaction_ratio"] - global_expression["strong_reaction_ratio"],
    }
    rounded = {name: round(value, 4) for name, value in comparisons.items()}
    profile["relative_to_global"] = {
        "deltas": rounded,
        "strongest_differences": [
            {"metric": name, "delta": value}
            for name, value in sorted(rounded.items(), key=lambda item: abs(item[1]), reverse=True)[:5]
        ],
    }


def render_report(profiles: list[dict[str, Any]], source_count: int) -> str:
    levels = Counter(item["confidence"]["level"] for item in profiles)
    lines = [
        "# Dyadic Profile Distillation Report",
        "",
        f"- Source files: {source_count}",
        f"- Profiles: {len(profiles)}",
        f"- High confidence: {levels['high']}",
        f"- Medium confidence: {levels['medium']}",
        f"- Low confidence: {levels['low']}",
        f"- Insufficient: {levels['insufficient']}",
        "",
        "| Person | Confidence | Private out/in | Group directed out/in | Avg chars | Burst | Initiation | Top topics |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in profiles[:80]:
        evidence = item["evidence"]
        expression = item["expression_pattern"]
        interaction = item["interaction_pattern"]
        topics = ", ".join(topic["label"] for topic in item["topics"]["shared_topics"][:4]) or "-"
        lines.append(
            "| {name} | {confidence} | {private_out}/{private_in} | {group_out}/{group_in} | {chars} | {burst} | {initiation} | {topics} |".format(
                name=item["canonical_name"].replace("|", "/"),
                confidence=item["confidence"]["level"],
                private_out=evidence["private_outgoing_count"],
                private_in=evidence["private_incoming_count"],
                group_out=evidence["group_directed_outgoing_count"],
                group_in=evidence["group_directed_incoming_count"],
                chars=expression["average_chars"],
                burst=interaction["average_burst_size"],
                initiation=interaction["initiation_ratio"],
                topics=topics,
            )
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Distill relationship-specific communication profiles.")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--relationship-dir", type=Path, default=DEFAULT_RELATIONSHIP_DIR)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runtime/dyadic-profiles/profiles.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("runtime/dyadic-profiles/distillation-report.md"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    alias_to_person, person_aliases = load_aliases(args.relationship_dir)
    profiles: dict[str, ProfileAccumulator] = {}
    source_paths = sorted(args.raw_dir.glob("*.json"))
    for path in source_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        session_type = str((data.get("session") or {}).get("type") or "")
        if session_type == "私聊" or path.name.startswith("私聊_"):
            process_private(path, data, alias_to_person, profiles)
        else:
            process_group(path, data, alias_to_person, profiles)

    rendered = [
        build_profile(profile, person_aliases.get(name, set()))
        for name, profile in profiles.items()
        if name and name not in SELF_NAMES
    ]
    global_profile = build_profile(merge_accumulators(profiles), set())
    for profile in rendered:
        add_global_contrast(profile, global_profile)
    rendered.sort(
        key=lambda item: (
            -item["confidence"]["weighted_sample_count"],
            item["canonical_name"],
        )
    )
    payload = {
        "version": "0.1",
        "source_manifest": {
            "raw_directory": str(args.raw_dir),
            "source_file_count": len(source_paths),
            "privacy_mode": "aggregate_only_no_raw_text",
        },
        "global_profile": global_profile,
        "profiles": rendered,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(rendered, len(source_paths)), encoding="utf-8")
    print(f"profiles={len(rendered)} output={args.output} report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
