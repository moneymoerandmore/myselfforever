#!/usr/bin/env python
"""Extract identity fact candidates from pre-distillation WeChat artifacts.

This script is intentionally conservative. It scans all self-message candidates
and all distilled episodes, then emits:

- a review report with short snippets for manual inspection
- candidate JSONL records for the SelfCore identity-facts module

It does not promote chat-derived candidates into confirmed facts by itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OUTPUTS = Path(r"C:\Users\cloud\Documents\Codex\2026-06-03\skill\outputs")
DEFAULT_REPORT = Path("workflows/distillation/reports/identity-fact-candidates.md")
DEFAULT_CANDIDATES = Path("runtime/self-core/identity-facts/candidates.jsonl")

TZ = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    fact_type: str
    keywords: tuple[str, ...]
    positive_patterns: tuple[str, ...]
    negative_patterns: tuple[str, ...]
    constraint_patterns: tuple[str, ...] = ()


THEMES = (
    Theme(
        key="cooking",
        label="做饭/下厨",
        fact_type="capability",
        keywords=("做饭", "做菜", "下厨", "炒菜", "烧菜", "煮饭", "煮菜", "厨房", "菜谱", "烤箱", "空气炸锅", "外卖"),
        positive_patterns=(r"我.{0,8}(会|能|可以).{0,8}(做饭|做菜|下厨|炒菜|烧菜)", r"(我来|我去).{0,6}(做饭|做菜|下厨|炒菜|烧菜)"),
        negative_patterns=(r"我.{0,8}(不会|不能|不太会|没法|完全不会).{0,8}(做饭|做菜|下厨|炒菜|烧菜)", r"(做饭|做菜|下厨|炒菜|烧菜).{0,8}(不会|不行|不太会)"),
        constraint_patterns=(r"(点外卖|外卖|下单|订餐)",),
    ),
    Theme(
        key="swimming",
        label="游泳/水性",
        fact_type="capability",
        keywords=("游泳", "会游", "不会游", "泳池", "蛙泳", "自由泳", "潜水", "水性", "溺水", "救生圈"),
        positive_patterns=(r"我.{0,8}(会|能|可以).{0,8}游泳", r"(会游泳|游得)"),
        negative_patterns=(r"我.{0,8}(不会|不能|不太会|没学会|怕).{0,8}游泳", r"(不会游泳|水性不好)"),
        constraint_patterns=(r"(怕水|深水|救生圈|溺水)",),
    ),
    Theme(
        key="driving",
        label="开车/驾照/自驾",
        fact_type="capability",
        keywords=("开车", "会开车", "不会开车", "驾照", "驾驶", "司机", "停车", "租车", "自驾", "科目二", "科目三", "车技"),
        positive_patterns=(r"我.{0,8}(会|能|可以).{0,8}(开车|驾驶)", r"(我来|我去).{0,6}(开车|开)", r"(有驾照|拿到驾照|考过驾照)"),
        negative_patterns=(r"我.{0,8}(不会|不能|不太会|没法|不敢).{0,8}(开车|驾驶)", r"(没驾照|没有驾照|驾照.{0,4}没有|不会开车)"),
        constraint_patterns=(r"(打车|叫车|司机|代驾|停车|租车)",),
    ),
    Theme(
        key="travel_planning",
        label="旅行规划",
        fact_type="habit",
        keywords=("行程", "酒店", "机票", "签证", "旅行", "旅游", "攻略", "路线", "订票", "订酒店"),
        positive_patterns=(r"我.{0,8}(定|订|安排|规划|做).{0,8}(行程|攻略|酒店|机票|路线)", r"(我来|我去).{0,6}(订|定|安排|规划)"),
        negative_patterns=(r"我.{0,8}(不会|不想|懒得).{0,8}(做攻略|规划|订酒店|订票)",),
    ),
    Theme(
        key="pets",
        label="养宠/猫",
        fact_type="role",
        keywords=("猫", "猫粮", "猫砂", "主子", "宠物", "兽医", "绝育", "铲屎"),
        positive_patterns=(r"我.{0,8}(家|养|的).{0,8}猫", r"(猫粮|猫砂|铲屎|兽医)"),
        negative_patterns=(),
    ),
    Theme(
        key="parenting",
        label="育儿/家庭照护",
        fact_type="role",
        keywords=("孩子", "小孩", "娃", "幼儿园", "上学", "育儿", "奶奶", "爸爸", "妈妈"),
        positive_patterns=(r"我.{0,8}(孩子|娃|女儿|儿子)", r"(幼儿园|育儿|奶奶|上学)"),
        negative_patterns=(),
    ),
    Theme(
        key="ai_product_work",
        label="AI/产品/组织工作",
        fact_type="habit",
        keywords=("AI", "模型", "prompt", "产品", "运营", "研发", "用户", "目标", "NPS", "dashboard"),
        positive_patterns=(r"(产品|运营|研发|用户|目标|NPS|AI|模型|prompt)",),
        negative_patterns=(),
    ),
)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def source_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def make_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def compact(text: str, limit: int = 140) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def load_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_line_no"] = line_no
            yield row


def row_text(row: dict[str, Any]) -> str:
    if "content_redacted" in row:
        return str(row.get("content_redacted", ""))
    return str(row.get("self_text_redacted", ""))


def row_ref(kind: str, row: dict[str, Any]) -> str:
    if kind == "candidate":
        return f"{row.get('source_file')}#localId={row.get('local_id')}"
    return str(row.get("episode_id", ""))


def polarity_for(theme: Theme, text: str) -> str | None:
    for pattern in theme.negative_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return "negative"
    for pattern in theme.positive_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return "positive"
    for pattern in theme.constraint_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return "constraint"
    return None


def scan_rows(path: Path, kind: str) -> dict[str, list[dict[str, Any]]]:
    matches: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in load_jsonl(path):
        text = row_text(row)
        if not text:
            continue
        if len(text) > 1800:
            # Long generated or copied blocks are poor identity-fact evidence.
            continue
        for theme in THEMES:
            if not any(keyword.lower() in text.lower() for keyword in theme.keywords):
                continue
            polarity = polarity_for(theme, text)
            matches[theme.key].append(
                {
                    "kind": kind,
                    "ref": row_ref(kind, row),
                    "source_hash": source_hash(str(row.get("source_file", ""))),
                    "chat_kind": row.get("chat_kind", ""),
                    "time": row.get("formatted_time") or row.get("start_formatted_time", ""),
                    "polarity": polarity or "mention",
                    "snippet": compact(text),
                    "message_chars": len(text),
                }
            )
    return matches


def merge_matches(*items: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    merged: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        for key, rows in item.items():
            for row in rows:
                dedupe_key = (key, str(row["kind"]), str(row["ref"]))
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                merged[key].append(row)
    return merged


def infer_candidate(theme: Theme, matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    counts = Counter(row["polarity"] for row in matches)
    evidence = [row for row in matches if row["polarity"] in {"positive", "negative", "constraint"}]
    if not evidence:
        return None

    if theme.key == "cooking":
        statement = "用户已显式校对：完全不会做饭；聊天抽取只作为旁证，不再生成相反候选。"
        runtime_rule = "涉及做饭时必须服从 confirmed fact：不得自称会做饭、愿意做饭、下厨或承担做饭。"
        confidence = "high"
        fact_type = "boundary"
        record_polarity = "constraint"
    elif theme.key == "swimming" and counts["positive"] == 0 and counts["negative"] == 0:
        statement = "全量语料未找到用户本人会/不会游泳的直接证据。"
        runtime_rule = "涉及游泳能力时不得替用户认领会游泳或不会游泳；除非用户现场确认，否则保持中性。"
        confidence = "low"
        fact_type = "boundary"
        record_polarity = "constraint"
    elif theme.key == "driving" and counts["positive"] >= 3:
        statement = "多次第一人称聊天证据显示：用户大概率会开车，并曾提到自己开车、开车接人或开车前往。"
        runtime_rule = "涉及开车能力时可以默认用户会开车，但不要替用户承诺当前一定能开、愿意开、适合开或有空开。"
        confidence = "medium"
        fact_type = "capability"
        record_polarity = "positive"
    elif counts["negative"] > counts["positive"] and counts["negative"] >= 2:
        polarity = "negative"
        statement = f"聊天证据倾向显示：用户在“{theme.label}”上不应被默认设定为会或愿意承担。"
        runtime_rule = f"涉及{theme.label}时，数字我不得主动自称会做或能承担；应保守表达，并优先请求确认。"
        confidence = "medium" if counts["negative"] >= 3 else "low"
        fact_type = "incapability"
        record_polarity = "negative"
    elif counts["positive"] >= 3 and counts["positive"] >= counts["negative"] * 2:
        polarity = "positive"
        statement = f"聊天证据倾向显示：用户经常涉及并可能熟悉“{theme.label}”。"
        runtime_rule = f"涉及{theme.label}时可以使用熟悉语气，但不要夸大为专业能力或承诺具体行动。"
        confidence = "medium" if counts["positive"] >= 6 else "low"
        fact_type = theme.fact_type
        record_polarity = "positive"
    elif counts["constraint"] >= 4 and theme.key in {"driving", "cooking", "travel_planning"}:
        polarity = "constraint"
        statement = f"聊天证据显示“{theme.label}”常作为安排方式或约束出现，但不足以证明能力本身。"
        runtime_rule = f"涉及{theme.label}时优先使用安排/协调表达，不要自动升级为能力事实。"
        confidence = "low"
        fact_type = "life_constraint"
        record_polarity = "constraint"
    else:
        polarity = "mixed"
        statement = f"关于“{theme.label}”存在多条聊天证据，但方向混杂，需要人工确认。"
        runtime_rule = f"涉及{theme.label}时不要自称确定会/不会，先使用中性表达或向用户确认。"
        confidence = "low"
        fact_type = "boundary"
        record_polarity = "constraint"

    preferred = [row for row in evidence if row["polarity"] == record_polarity]
    if not preferred and record_polarity == "constraint":
        preferred = evidence
    if not preferred:
        preferred = evidence
    top_evidence = sorted(
        preferred,
        key=lambda row: (row["polarity"] != "mention", row["time"]),
        reverse=True,
    )[:12]
    refs = [str(row["ref"]) for row in top_evidence[:8]]
    record_id = f"ifc-20260710-{theme.key}-{make_id(statement + '|'.join(refs))}"
    return {
        "id": record_id,
        "created_at": now_iso(),
        "updated_at": None,
        "fact_type": fact_type,
        "polarity": record_polarity,
        "statement": statement,
        "runtime_rule": runtime_rule,
        "confidence": confidence,
        "source_type": "chat_extraction",
        "evidence_refs": refs,
        "confirmed_by_user": False,
        "status": "active",
        "supersedes": [],
        "notes": f"Auto-extracted from full self candidates and full episodes. polarity_counts={dict(counts)}",
    }


def render_table(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        values = [str(row.get(column, "")).replace("|", "/") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs-dir", type=Path, default=DEFAULT_OUTPUTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--sample-size", type=int, default=16)
    args = parser.parse_args()

    self_candidates_path = args.outputs_dir / "wechat-full-self-candidates.jsonl"
    full_episodes_path = args.outputs_dir / "wechat-full-episodes.jsonl"
    if not self_candidates_path.exists():
        raise FileNotFoundError(self_candidates_path)
    if not full_episodes_path.exists():
        raise FileNotFoundError(full_episodes_path)

    matches = merge_matches(
        scan_rows(self_candidates_path, "candidate"),
        scan_rows(full_episodes_path, "episode"),
    )

    candidate_records = []
    for theme in THEMES:
        candidate = infer_candidate(theme, matches.get(theme.key, []))
        if candidate:
            candidate_records.append(candidate)

    args.candidates.parent.mkdir(parents=True, exist_ok=True)
    with args.candidates.open("w", encoding="utf-8", newline="\n") as handle:
        for record in candidate_records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    lines: list[str] = []
    lines.append("# 身份事实候选抽取报告")
    lines.append("")
    lines.append(f"- Generated: {now_iso()}")
    lines.append(f"- Source outputs: `{args.outputs_dir}`")
    lines.append(f"- Candidate output: `{args.candidates}`")
    lines.append("- Privacy posture: snippets are short review excerpts; confirmed facts should still cite refs instead of copying long chat text.")
    lines.append("")
    lines.append("## 结论")
    lines.append("")
    lines.append("- 用户显式校对的做饭事实优先级最高：用户完全不会做饭，数字我不得自称会做饭或愿意做饭。")
    lines.append("- 本轮聊天抽取只产出候选，不自动提升为 confirmed facts。")
    lines.append("- 对游泳、开车这类能力事实，如果没有直接“我会/我不会”的强证据，运行时应保持中性，不替用户认领。")
    lines.append("")

    summary_rows = []
    for theme in THEMES:
        rows = matches.get(theme.key, [])
        counts = Counter(row["polarity"] for row in rows)
        summary_rows.append(
            {
                "theme": theme.label,
                "matches": len(rows),
                "positive": counts["positive"],
                "negative": counts["negative"],
                "constraint": counts["constraint"],
                "mention": counts["mention"],
            }
        )
    lines.append("## Theme Summary")
    lines.append("")
    lines.extend(render_table(summary_rows, ["theme", "matches", "positive", "negative", "constraint", "mention"]))
    lines.append("")

    lines.append("## Candidate Records")
    lines.append("")
    if candidate_records:
        lines.extend(
            render_table(
                [
                    {
                        "id": row["id"],
                        "fact_type": row["fact_type"],
                        "polarity": row["polarity"],
                        "confidence": row["confidence"],
                        "statement": row["statement"],
                    }
                    for row in candidate_records
                ],
                ["id", "fact_type", "polarity", "confidence", "statement"],
            )
        )
    else:
        lines.append("- None.")
    lines.append("")

    lines.append("## Evidence Samples")
    lines.append("")
    for theme in THEMES:
        rows = matches.get(theme.key, [])
        lines.append(f"### {theme.label}")
        if not rows:
            lines.append("- No matches.")
            lines.append("")
            continue
        sample = sorted(
            rows,
            key=lambda row: (
                {"negative": 3, "positive": 2, "constraint": 1, "mention": 0}.get(str(row["polarity"]), 0),
                str(row["time"]),
            ),
            reverse=True,
        )[: args.sample_size]
        lines.extend(render_table(sample, ["kind", "ref", "time", "polarity", "source_hash", "snippet"]))
        lines.append("")

    lines.append("## Manual Promotion Rules")
    lines.append("")
    lines.append("1. 用户显式纠错 > 多次强证据 > 单次聊天提及。")
    lines.append("2. 能力事实必须有直接表达，比如“我会/不会/不敢/没驾照”；仅出现行程、停车、司机、外卖，不等于能力。")
    lines.append("3. 旅行、AI、工作等高频主题可以作为偏好或熟悉领域候选，但不要写成身份、职业或承诺。")
    lines.append("4. 任何涉及家庭、公司、真实姓名、住址、健康和财务的事实，默认留在候选或关系层，不直接公开进 SelfCore。")
    lines.append("")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.report}")
    print(f"Wrote {args.candidates}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
