#!/usr/bin/env python
"""Minimal local draft generator for the digital twin project.

This is intentionally rule-based. It uses the existing relationship CSV as
context, then emits a draft plus rationale and risk notes. It does not call any
external model or copy private relationship data into this repository.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


DEFAULT_RELATIONSHIP_CSV = (
    r"C:\Users\cloud\Documents\Codex\2026-06-09\new-chat\outputs"
    r"\relationship_dimensions.csv"
)


INTENTS = {
    "casual_chat",
    "work_discussion",
    "decision_request",
    "emotional_support",
    "family_coordination",
    "investment_discussion",
    "news_discussion",
    "logistics",
    "conflict",
    "unknown",
}


@dataclass
class PersonContext:
    display_name: str
    call_name: str
    wechat_name: str
    person_name: str
    node_type: str
    objective_relationship: str
    relationship_positioning: str
    interest_circles: str
    main_scenes: str
    frequent_topics: str
    call_evidence: str
    match_score: int
    call_name_confidence: str


@dataclass
class DraftOutput:
    query: str
    mode: str
    intent: str
    scenario: str
    draft_text: str
    relationship_basis: str
    topic_basis: str
    tone_basis: str
    risk_level: str
    approval_required: bool
    questions_for_user: list[str]
    person: dict[str, Any] | None
    candidates: list[dict[str, Any]]


def read_people(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def text(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def infer_call_confidence(row: dict[str, str]) -> str:
    call = text(row, "称呼名")
    wechat = text(row, "微信名")
    evidence = text(row, "称呼证据")
    if evidence:
        return "strong"
    if call and wechat and call != wechat:
        return "candidate"
    if call and call == wechat:
        return "unknown"
    return "unknown"


def row_to_person(row: dict[str, str], score: int) -> PersonContext:
    return PersonContext(
        display_name=text(row, "展示名称"),
        call_name=text(row, "称呼名"),
        wechat_name=text(row, "微信名"),
        person_name=text(row, "人物"),
        node_type=text(row, "节点类型"),
        objective_relationship=text(row, "客观关系"),
        relationship_positioning=text(row, "关系定位"),
        interest_circles=text(row, "兴趣/活动圈层"),
        main_scenes=text(row, "主要场景"),
        frequent_topics=text(row, "高频主题"),
        call_evidence=text(row, "称呼证据"),
        match_score=score,
        call_name_confidence=infer_call_confidence(row),
    )


def resolve_people(rows: list[dict[str, str]], query: str, limit: int = 5) -> list[PersonContext]:
    needle = query.strip().lower()
    if not needle:
        return []

    matches: list[PersonContext] = []
    searchable_keys = ["展示名称", "称呼名", "微信名", "人物", "关系定位", "高频主题"]
    exact_keys = ["展示名称", "称呼名", "微信名", "人物"]

    for row in rows:
        score = 0
        values = [text(row, key) for key in searchable_keys]
        exact_values = [text(row, key) for key in exact_keys]

        if any(needle == value.lower() for value in exact_values if value):
            score = 100
        elif any(needle in value.lower() for value in exact_values if value):
            score = 80
        elif any(needle in value.lower() for value in values if value):
            score = 55

        if score:
            if text(row, "节点类型") == "直接微信关系":
                score += 10
            if text(row, "称呼证据"):
                score += 5
            matches.append(row_to_person(row, score))

    matches.sort(key=lambda person: person.match_score, reverse=True)
    return matches[:limit]


def relationship_group(person: PersonContext | None) -> str:
    if not person:
        return "unknown"
    if "间接" in person.objective_relationship or person.node_type == "被提及":
        return "mentioned"
    relation = person.objective_relationship
    if "亲人" in relation or "亲戚" in relation or "姻亲" in relation:
        return "family"
    if "同事" in relation:
        return "coworker"
    if "同学" in relation or "朋友" in relation:
        return "friend"
    if "服务" in relation or "事务" in relation:
        return "service"
    return "unknown"


def risk_level(person: PersonContext | None, intent: str, scenario: str) -> tuple[str, bool, list[str]]:
    reasons: list[str] = []
    level = "R1_low"

    if not person:
        return "R3_high", True, ["未识别联系人，需要先确认身份。"]

    group = relationship_group(person)
    scenario_lower = scenario.lower()
    sensitive_terms = [
        "投资",
        "股票",
        "买入",
        "卖出",
        "钱",
        "金额",
        "法律",
        "医疗",
        "道歉",
        "承诺",
        "冲突",
        "吵",
        "离职",
        "公司",
        "组织",
        "内部",
        "项目",
        "群聊",
        "老板",
        "家庭",
        "孩子",
    ]

    if group == "mentioned":
        level = "R3_high"
        reasons.append("该人物是间接提及节点，不应主动或假装熟悉。")

    if intent in {"investment_discussion", "conflict", "family_coordination"}:
        level = "R2_medium"
        reasons.append(f"意图 `{intent}` 需要用户确认。")

    if group == "family" and intent in {"conflict", "family_coordination", "emotional_support"}:
        level = "R3_high"
        reasons.append("家庭/亲密关系场景情绪和边界风险高。")

    if group == "coworker" and intent in {"work_discussion", "decision_request"}:
        level = max_risk(level, "R2_medium")
        reasons.append("工作场景可能涉及内部信息或具体人评价。")

    if any(term in scenario_lower for term in sensitive_terms):
        level = max_risk(level, "R2_medium")
        reasons.append("场景包含敏感词，需要确认措辞。")

    if intent == "logistics" and level == "R1_low":
        level = "R0_safe"

    return level, level != "R0_safe", reasons


def max_risk(left: str, right: str) -> str:
    order = ["R0_safe", "R1_low", "R2_medium", "R3_high", "R4_forbidden"]
    return order[max(order.index(left), order.index(right))]


def safe_address(person: PersonContext | None) -> str:
    if not person:
        return ""
    if person.call_name_confidence in {"strong", "locked"} and person.call_name:
        return person.call_name
    return ""


def make_draft(person: PersonContext | None, intent: str, scenario: str, mode: str) -> tuple[str, str]:
    group = relationship_group(person)
    address = safe_address(person)
    prefix = f"{address}\n" if address else ""

    if not person:
        return (
            "我还没确认这个联系人是谁。\n"
            "先不要生成对外消息。\n"
            "请先确认 TA 是否是直接微信关系、你们是什么关系、这次要聊什么。",
            "identity_confirmation_required",
        )

    if group == "mentioned":
        return (
            "这个人目前只是关系图谱里的被提及节点。\n"
            "我不建议直接生成对外消息。\n"
            "先确认一下 TA 是谁、你们什么关系、有没有直接沟通渠道。",
            "observe_only",
        )

    if intent == "logistics":
        return (
            prefix
            + "可以\n"
            + "我先确认一下时间和具体要做的事\n"
            + "你把最关键的信息发我\n"
            + "我来对一下",
            "concise_logistics",
        )

    if intent == "investment_discussion":
        return (
            prefix
            + "这个反应有点意思\n"
            + "但先别急着翻译成利好利空\n"
            + "问题是现在大家是不是都在讲同一个故事\n"
            + "如果预期已经打满了\n"
            + "那反而要小心\n"
            + "我先不下结论，这个方向可以盯",
            "analytical_non_advice",
        )

    if intent == "emotional_support":
        return (
            prefix
            + "这个先别全算到自己头上\n"
            + "你不是没做\n"
            + "是已经扛了太多乱七八糟的东西\n"
            + "先挑最烦的那一件\n"
            + "我们把它拆小一点\n"
            + "不然脑子会一直空转",
            "direct_supportive_decomposition",
        )

    if intent == "news_discussion":
        return (
            prefix
            + "这个新闻还挺值得看\n"
            + "表面看是一个事件\n"
            + "但我觉得重点不是这个事本身\n"
            + "是后面谁的激励会变\n"
            + "如果激励变了\n"
            + "后面动作肯定也会变\n"
            + "这个新变量比新闻标题重要",
            "news_structure_probe",
        )

    if intent == "family_coordination" or group == "family":
        return (
            prefix
            + "这事先别上价值\n"
            + "先拆一下到底卡在哪\n"
            + "是时间没排开\n"
            + "还是默认有个人要兜底\n"
            + "如果只是安排问题，就按安排解决\n"
            + "别最后变成情绪账\n"
            + "今天先把必须定的那一件事定掉",
            "family_fact_chain_decomposition",
        )

    if intent == "work_discussion" or group == "coworker":
        return (
            prefix
            + "我感觉这个问题不是要不要做\n"
            + "而是目标到底是哪一个\n"
            + "如果目标都没对齐\n"
            + "后面讨论方案基本就是空转\n"
            + "先把口径拉直\n"
            + "现在真正的分歧是什么？",
            "analytical_goal_alignment",
        )

    return (
        prefix
        + "这个有点意思\n"
        + "我感觉不是表面这么简单\n"
        + "先看看后面怎么演\n"
        + "如果真按这个方向走\n"
        + "可能反而有新变量",
        "casual_structural_take",
    )


def build_output(
    query: str,
    scenario: str,
    intent: str,
    mode: str,
    matches: list[PersonContext],
) -> DraftOutput:
    person = matches[0] if matches else None
    level, approval_required, risk_reasons = risk_level(person, intent, scenario)
    draft, tone = make_draft(person, intent, scenario, mode)

    questions: list[str] = []
    if not person:
        questions.append("这个联系人是谁？是否是直接微信关系？")
    elif person.node_type != "直接微信关系":
        questions.append("是否确认这是可以直接沟通的人？")
    if person and person.call_name_confidence in {"candidate", "unknown"}:
        questions.append("这个称呼是否符合你平时真实叫法？")
    if risk_reasons:
        questions.extend(risk_reasons)

    relationship_basis = "未识别联系人"
    topic_basis = "未检索到共同话题"
    if person:
        relationship_basis = (
            f"{person.objective_relationship}；{person.relationship_positioning or '暂无关系定位'}"
        )
        topic_basis = person.frequent_topics or person.interest_circles or "暂无高频主题"

    candidates = [
        {
            "display_name": item.display_name,
            "objective_relationship": item.objective_relationship,
            "node_type": item.node_type,
            "match_score": item.match_score,
            "call_name_confidence": item.call_name_confidence,
        }
        for item in matches[1:]
    ]

    return DraftOutput(
        query=query,
        mode=mode,
        intent=intent,
        scenario=scenario,
        draft_text=draft,
        relationship_basis=relationship_basis,
        topic_basis=topic_basis,
        tone_basis=tone,
        risk_level=level,
        approval_required=approval_required,
        questions_for_user=questions,
        person=asdict(person) if person else None,
        candidates=candidates,
    )


def render_markdown(output: DraftOutput) -> str:
    lines = [
        "# Draft Output",
        "",
        "## 草稿",
        "",
        output.draft_text,
        "",
        "## 依据",
        "",
        f"- 查询：`{output.query}`",
        f"- 意图：`{output.intent}`",
        f"- 场景：{output.scenario}",
        f"- 关系依据：{output.relationship_basis}",
        f"- 话题依据：{output.topic_basis}",
        f"- 语气依据：`{output.tone_basis}`",
        "",
        "## 风险",
        "",
        f"- 风险等级：`{output.risk_level}`",
        f"- 需要确认：`{str(output.approval_required).lower()}`",
    ]

    if output.questions_for_user:
        lines.extend(["", "## 需要确认", ""])
        lines.extend(f"- {question}" for question in output.questions_for_user)

    if output.candidates:
        lines.extend(["", "## 其他候选", ""])
        for candidate in output.candidates:
            lines.append(
                "- {display_name} / {objective_relationship} / score={match_score}".format(
                    **candidate
                )
            )

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a local communication draft.")
    parser.add_argument("--query", required=True, help="Contact name, call name, or nickname.")
    parser.add_argument("--scenario", required=True, help="Current message or communication scenario.")
    parser.add_argument("--intent", default="unknown", choices=sorted(INTENTS))
    parser.add_argument("--mode", default="draft", choices=["observe", "draft", "assist_send"])
    parser.add_argument("--csv", default=DEFAULT_RELATIONSHIP_CSV, help="Relationship dimensions CSV path.")
    parser.add_argument("--format", default="markdown", choices=["markdown", "json"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"relationship CSV not found: {csv_path}")

    rows = read_people(csv_path)
    matches = resolve_people(rows, args.query)
    output = build_output(args.query, args.scenario, args.intent, args.mode, matches)

    if args.format == "json":
        print(json.dumps(asdict(output), ensure_ascii=False, indent=2))
    else:
        print(render_markdown(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
