#!/usr/bin/env python
"""Deeper scan for identity, capability, preference, and life-role signals.

This is a broad discovery report, not an automatic promotion pipeline. It
answers: "Does the pre-distillation corpus contain more personal facts/skills
than the narrow cooking/swimming/driving probe found?"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OUTPUTS = Path(r"C:\Users\cloud\Documents\Codex\2026-06-03\skill\outputs")
DEFAULT_REPORT = Path("workflows/distillation/reports/identity-signal-deep-scan.md")
TZ = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    keywords: tuple[str, ...]


CATEGORIES = (
    Category("ai_product", "AI/产品/组织/研发/运营", ("ai", "AI", "模型", "prompt", "产品", "运营", "研发", "用户", "需求", "NPS", "组织", "管理", "目标", "项目", "dashboard", "json", "代码")),
    Category("investment", "投资/市场/股票/资产", ("股票", "基金", "港股", "A股", "美股", "买入", "卖出", "仓位", "抄底", "止盈", "亏", "涨", "跌", "财报", "估值", "目标价", "投资")),
    Category("travel", "旅行/行程/订票订酒店", ("旅行", "旅游", "行程", "攻略", "酒店", "机票", "火车", "签证", "自驾", "租车", "景点", "机场", "高铁", "订票", "定酒店", "订酒店")),
    Category("parenting", "育儿/孩子教育", ("孩子", "女儿", "娃", "宝宝", "幼儿园", "上学", "教育", "育儿", "奶奶", "陪读", "社交", "入园")),
    Category("pets", "猫/宠物照护", ("猫", "猫粮", "猫砂", "铲屎", "宠物", "兽医", "投喂", "主子", "绝育")),
    Category("food", "吃饭/外卖/选店", ("吃饭", "外卖", "餐厅", "店", "菜单", "点菜", "下单", "奶茶", "咖啡", "火锅", "烧烤", "食堂")),
    Category("cooking", "做饭/下厨", ("做饭", "做菜", "下厨", "炒菜", "烧菜", "煮饭", "煮菜", "厨房", "菜谱", "烤箱", "空气炸锅")),
    Category("driving", "开车/停车/接送", ("开车", "驾照", "驾驶", "停车", "车位", "接你", "接你们", "打车", "司机", "自驾")),
    Category("swimming", "游泳/水性", ("游泳", "会游泳", "不会游泳", "泳池", "潜水", "溺水", "水性")),
    Category("gaming", "游戏/娱乐", ("游戏", "打游戏", "lol", "LOL", "王者", "塞尔达", "switch", "steam", "原神", "电竞", "比赛")),
    Category("health", "健康/医疗/体检", ("医院", "看病", "体检", "血糖", "尿酸", "医生", "药", "发烧", "感冒", "睡眠", "焦虑", "心理", "运动")),
    Category("housing_city", "住房/城市/装修/搬家", ("房子", "买房", "租房", "装修", "搬家", "城市", "小区", "物业", "停车位", "户口", "上海", "杭州", "香港")),
    Category("shopping", "购物/消费/品牌", ("买", "下单", "价格", "打折", "优惠", "信用卡", "LV", "爱马仕", "淘宝", "京东", "拼多多", "退税")),
    Category("writing_speaking", "写作/表达/汇报/PPT", ("写", "文档", "汇报", "PPT", "邮件", "方案", "总结", "复盘", "发言", "表达", "讲")),
    Category("social_relationship", "关系/社交/沟通", ("朋友", "同事", "老板", "沟通", "关系", "家人", "老婆", "妈妈", "爸爸", "同学", "群", "约")),
)


DIRECT_PATTERNS = {
    "ability_positive": re.compile(r"(我|本人|自己).{0,8}(会|能|可以|擅长|熟|懂|搞得定|做过|学过|考过|拿到).{0,18}"),
    "ability_negative": re.compile(r"(我|本人|自己).{0,8}(不会|不能|不太会|不懂|不熟|不擅长|没学过|不敢|搞不定|完全不会).{0,18}"),
    "responsibility": re.compile(r"(我来|我去|我负责|我定|我订|我安排|我下单|我买|我接|我送|我处理|我搞|我写|我做).{0,18}"),
    "preference_positive": re.compile(r"(我|本人|自己).{0,8}(喜欢|爱|想|愿意|倾向|偏好|看好|认可).{0,18}"),
    "preference_negative": re.compile(r"(我|本人|自己).{0,8}(不喜欢|讨厌|反感|不想|不愿意|不看好|不认可).{0,18}"),
    "life_role": re.compile(r"(我家|我们家|我女儿|我孩子|我老婆|我妈|我爸|我同事|我老板|我团队).{0,24}"),
}

COPYLIKE_MARKERS = ("###", "---", "一、", "二、", "三、", "干预建议", "完整行程", "参考文献")


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def source_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def compact(text: str, limit: int = 120) -> str:
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
    return str(row.get("content_redacted") or row.get("self_text_redacted") or "")


def is_copylike(text: str) -> bool:
    if len(text) > 1200:
        return True
    return sum(marker in text for marker in COPYLIKE_MARKERS) >= 2


def category_hits(text: str) -> list[str]:
    lowered = text.lower()
    hits = []
    for category in CATEGORIES:
        if any(keyword.lower() in lowered for keyword in category.keywords):
            hits.append(category.key)
    return hits


def direct_signal_types(text: str) -> list[str]:
    hits = []
    for name, pattern in DIRECT_PATTERNS.items():
        if pattern.search(text):
            hits.append(name)
    return hits


def extract_phrase(text: str, signal_type: str) -> str:
    pattern = DIRECT_PATTERNS[signal_type]
    match = pattern.search(text)
    if not match:
        return compact(text)
    start = max(match.start() - 16, 0)
    end = min(match.end() + 32, len(text))
    return compact(text[start:end])


def scan(path: Path, kind: str) -> tuple[list[dict[str, Any]], Counter[str], dict[str, Counter[str]]]:
    rows: list[dict[str, Any]] = []
    category_counter: Counter[str] = Counter()
    category_signal_counter: dict[str, Counter[str]] = defaultdict(Counter)

    for row in load_jsonl(path):
        text = row_text(row)
        if not text or is_copylike(text):
            continue
        categories = category_hits(text)
        if not categories:
            continue
        signal_types = direct_signal_types(text)
        for category in categories:
            category_counter[category] += 1
            for signal_type in signal_types:
                category_signal_counter[category][signal_type] += 1
        if not signal_types:
            continue
        for category in categories:
            for signal_type in signal_types:
                rows.append(
                    {
                        "category": category,
                        "signal_type": signal_type,
                        "kind": kind,
                        "ref": f"{row.get('source_file')}#localId={row.get('local_id')}" if kind == "candidate" else row.get("episode_id", ""),
                        "time": row.get("formatted_time") or row.get("start_formatted_time", ""),
                        "chat_kind": row.get("chat_kind", ""),
                        "source_hash": source_hash(str(row.get("source_file", ""))),
                        "phrase": extract_phrase(text, signal_type),
                    }
                )
    return rows, category_counter, category_signal_counter


def merge_signal_rows(*chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    merged: list[dict[str, Any]] = []
    for rows in chunks:
        for row in rows:
            key = (str(row["category"]), str(row["signal_type"]), str(row["kind"]), str(row["ref"]))
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
    return merged


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
    parser.add_argument("--sample-size", type=int, default=12)
    args = parser.parse_args()

    candidate_path = args.outputs_dir / "wechat-full-self-candidates.jsonl"
    episode_path = args.outputs_dir / "wechat-full-episodes.jsonl"
    if not candidate_path.exists():
        raise FileNotFoundError(candidate_path)
    if not episode_path.exists():
        raise FileNotFoundError(episode_path)

    c_rows, c_cat, c_sig = scan(candidate_path, "candidate")
    e_rows, e_cat, e_sig = scan(episode_path, "episode")
    rows = merge_signal_rows(c_rows, e_rows)
    category_counter = c_cat + e_cat
    category_signal_counter: dict[str, Counter[str]] = defaultdict(Counter)
    for category in set(c_sig) | set(e_sig):
        category_signal_counter[category] = c_sig[category] + e_sig[category]

    category_labels = {category.key: category.label for category in CATEGORIES}
    summary_rows = []
    for category in CATEGORIES:
        signals = category_signal_counter[category.key]
        summary_rows.append(
            {
                "category": category.label,
                "mentions": category_counter[category.key],
                "direct_signals": sum(signals.values()),
                "ability+": signals["ability_positive"],
                "ability-": signals["ability_negative"],
                "responsibility": signals["responsibility"],
                "pref+": signals["preference_positive"],
                "pref-": signals["preference_negative"],
                "role": signals["life_role"],
            }
        )

    lines: list[str] = []
    lines.append("# 身份信号深挖报告")
    lines.append("")
    lines.append(f"- Generated: {now_iso()}")
    lines.append(f"- Source outputs: `{args.outputs_dir}`")
    lines.append("- Scope: full self-message candidates plus full episodes; long copylike blocks skipped.")
    lines.append("")
    lines.append("## 结论")
    lines.append("")
    lines.append("- 上一轮只做了窄口径能力事实抽取，不代表语料里事实/技能项很少。")
    lines.append("- 全量语料包含大量身份信号，但大部分是“熟悉领域/生活角色/偏好/常承担的事”，不能直接升格成硬事实。")
    lines.append("- 能力类事实需要更严格：必须有直接第一人称证据，或者用户确认。否则只进候选或未知项。")
    lines.append("")
    lines.append("## Category Summary")
    lines.append("")
    lines.extend(render_table(summary_rows, ["category", "mentions", "direct_signals", "ability+", "ability-", "responsibility", "pref+", "pref-", "role"]))
    lines.append("")

    lines.append("## High-Value Findings")
    lines.append("")
    lines.append("- 强事实：不会做饭来自用户显式校对，不依赖聊天挖掘。")
    lines.append("- 中置信能力：开车有多次第一人称证据，可作为“会开车，但不承诺当下能开/愿意开”的约束。")
    lines.append("- 未知能力：游泳缺少用户本人能力表达，不能认领。")
    lines.append("- 稳定熟悉领域：AI/产品/组织、投资/市场、旅行规划、育儿、猫/宠物、游戏、健康医疗、住房城市、购物消费、写作汇报。")
    lines.append("- 这些熟悉领域更适合进入 `candidates.jsonl` 或 SelfCore 的“身份事实候选/熟悉领域”，不宜全部写成 confirmed facts。")
    lines.append("")

    lines.append("## Signal Samples")
    lines.append("")
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_category[str(row["category"])].append(row)

    signal_weight = {
        "ability_negative": 6,
        "ability_positive": 5,
        "responsibility": 4,
        "preference_negative": 3,
        "preference_positive": 2,
        "life_role": 1,
    }
    for category in CATEGORIES:
        lines.append(f"### {category.label}")
        samples = sorted(
            by_category.get(category.key, []),
            key=lambda row: (signal_weight.get(str(row["signal_type"]), 0), str(row["time"])),
            reverse=True,
        )[: args.sample_size]
        if not samples:
            lines.append("- No direct signals.")
        else:
            display = [
                {
                    **row,
                    "category": category_labels.get(str(row["category"]), str(row["category"])),
                }
                for row in samples
            ]
            lines.extend(render_table(display, ["signal_type", "kind", "ref", "time", "source_hash", "phrase"]))
        lines.append("")

    lines.append("## Promotion Guidance")
    lines.append("")
    lines.append("1. `ability_positive/ability_negative` 可进入候选；只有用户确认或多次明确第一人称证据才进 facts。")
    lines.append("2. `responsibility` 表示用户经常承担某类安排，不等于永久承诺。例如定酒店、写方案、接送都要保留当下确认。")
    lines.append("3. `life_role` 常含家庭/关系隐私，默认只用于本地运行时，不公开进入生成内容。")
    lines.append("4. 高频熟悉领域用于让数字我“不装陌生”，但不能让它“装专业”或替用户作现实承诺。")
    lines.append("")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
