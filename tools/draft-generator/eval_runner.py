#!/usr/bin/env python
"""Run executable evals against the minimal draft generator."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from draft_generator import (
    DEFAULT_RELATIONSHIP_CSV,
    build_output,
    read_people,
    resolve_people,
)


RISK_ORDER = ["R0_safe", "R1_low", "R2_medium", "R3_high", "R4_forbidden"]


def risk_at_least(actual: str, expected_min: str) -> bool:
    return RISK_ORDER.index(actual) >= RISK_ORDER.index(expected_min)


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return cases


def contains_all(haystack: str, needles: list[str]) -> list[str]:
    return [needle for needle in needles if needle not in haystack]


def contains_none(haystack: str, needles: list[str]) -> list[str]:
    return [needle for needle in needles if needle in haystack]


def evaluate_case(case: dict[str, Any], rows: list[dict[str, str]]) -> dict[str, Any]:
    matches = resolve_people(rows, case["query"])
    output = build_output(
        query=case["query"],
        scenario=case["scenario"],
        intent=case.get("intent", "unknown"),
        mode=case.get("mode", "draft"),
        matches=matches,
    )

    failures: list[str] = []
    output_dict = asdict(output)
    joined_questions = "\n".join(output.questions_for_user)

    expected_min_risk = case.get("expected_min_risk")
    if expected_min_risk and not risk_at_least(output.risk_level, expected_min_risk):
        failures.append(f"risk {output.risk_level} < {expected_min_risk}")

    if "expected_approval_required" in case:
        expected = bool(case["expected_approval_required"])
        if output.approval_required != expected:
            failures.append(f"approval_required {output.approval_required} != {expected}")

    missing = contains_all(output.draft_text, case.get("draft_contains", []))
    if missing:
        failures.append("draft missing: " + ", ".join(missing))

    forbidden = contains_none(output.draft_text, case.get("draft_not_contains", []))
    if forbidden:
        failures.append("draft forbidden: " + ", ".join(forbidden))

    missing_questions = contains_all(joined_questions, case.get("questions_contain", []))
    if missing_questions:
        failures.append("questions missing: " + ", ".join(missing_questions))

    relationship_contains = case.get("relationship_contains")
    if relationship_contains and relationship_contains not in output.relationship_basis:
        failures.append(f"relationship missing: {relationship_contains}")

    person_node_type = case.get("person_node_type")
    if person_node_type:
        actual_node_type = (output.person or {}).get("node_type")
        if actual_node_type != person_node_type:
            failures.append(f"node_type {actual_node_type} != {person_node_type}")

    return {
        "id": case["id"],
        "passed": not failures,
        "failures": failures,
        "risk_level": output.risk_level,
        "approval_required": output.approval_required,
        "tone_basis": output.tone_basis,
        "relationship_basis": output.relationship_basis,
        "output": output_dict,
    }


def render_markdown(results: list[dict[str, Any]]) -> str:
    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    lines = [
        "# Draft Generator Eval Report",
        "",
        f"- Total: {total}",
        f"- Passed: {passed}",
        f"- Failed: {total - passed}",
        "",
        "| Case | Result | Risk | Approval | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        notes = "; ".join(result["failures"]) if result["failures"] else ""
        lines.append(
            "| {id} | {status} | `{risk}` | `{approval}` | {notes} |".format(
                id=result["id"],
                status=status,
                risk=result["risk_level"],
                approval=str(result["approval_required"]).lower(),
                notes=notes.replace("|", "/"),
            )
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run draft generator eval cases.")
    parser.add_argument(
        "--cases",
        default=str(Path(__file__).with_name("eval_cases.jsonl")),
        help="JSONL eval cases path.",
    )
    parser.add_argument("--csv", default=DEFAULT_RELATIONSHIP_CSV, help="Relationship CSV path.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", help="Optional report output path.")
    parser.add_argument("--no-fail", action="store_true", help="Always exit 0.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = load_cases(Path(args.cases))
    rows = read_people(Path(args.csv))
    results = [evaluate_case(case, rows) for case in cases]

    if args.format == "json":
        rendered = json.dumps(results, ensure_ascii=False, indent=2)
    else:
        rendered = render_markdown(results)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)

    failed = any(not result["passed"] for result in results)
    if failed and not args.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
