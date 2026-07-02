#!/usr/bin/env python
"""Audit the WeChat distillation episode layers before SelfCore/skill work.

The source JSONL files live outside this repository. This script keeps reports
lightweight and traceable without copying chat text into git-tracked files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any


DEFAULT_OUTPUTS = Path(r"C:\Users\cloud\Documents\Codex\2026-06-03\skill\outputs")
DEFAULT_REPORT = Path("workflows/distillation/reports/pre-distillation-corpus-audit.md")

LAYER_FILES = {
    "core": "wechat-distill-core-episodes.jsonl",
    "style": "wechat-distill-style-episodes.jsonl",
    "counter": "wechat-distill-counterexample-episodes.jsonl",
    "background": "wechat-distill-background-episodes.jsonl",
}

SCORE_KEYS = ("three_views", "worldview", "lifeview", "values", "thinking", "style", "counter")


def source_hash(source_file: str) -> str:
    return hashlib.sha1(source_file.encode("utf-8")).hexdigest()[:10]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def pct(values: list[int | float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = round((len(ordered) - 1) * q)
    return float(ordered[idx])


def score_summary(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    values = [int(row.get("bucket_scores", {}).get(key, 0) or 0) for row in rows]
    if not values:
        return {"min": 0, "p50": 0, "p90": 0, "max": 0, "avg": 0}
    return {
        "min": min(values),
        "p50": pct(values, 0.5),
        "p90": pct(values, 0.9),
        "max": max(values),
        "avg": round(mean(values), 2),
    }


def compact_episode(row: dict[str, Any]) -> dict[str, Any]:
    scores = row.get("bucket_scores", {})
    return {
        "episode_id": row.get("episode_id", ""),
        "bucket": row.get("bucket", ""),
        "line_no": row.get("_line_no", ""),
        "three_views": scores.get("three_views", 0),
        "worldview": scores.get("worldview", 0),
        "lifeview": scores.get("lifeview", 0),
        "values": scores.get("values", 0),
        "thinking": scores.get("thinking", 0),
        "style": scores.get("style", 0),
        "counter": scores.get("counter", 0),
        "message_count": row.get("message_count", 0),
        "avg_chars": row.get("avg_chars_per_message", 0),
        "max_single_chars": row.get("max_single_chars", 0),
        "tags": ",".join(row.get("tags", [])[:6]),
        "source_hash": source_hash(str(row.get("source_file", ""))),
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
    parser.add_argument("--sample-size", type=int, default=12)
    args = parser.parse_args()

    layers: dict[str, list[dict[str, Any]]] = {}
    for layer, filename in LAYER_FILES.items():
        path = args.outputs_dir / filename
        if not path.exists():
            raise FileNotFoundError(path)
        layers[layer] = load_jsonl(path)

    all_rows = [row for rows in layers.values() for row in rows]
    by_episode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        by_episode[str(row.get("episode_id", ""))].append(row)

    duplicate_episode_ids = sorted(
        episode_id for episode_id, rows in by_episode.items() if len(rows) > 1
    )
    missing_score_rows = [row for row in all_rows if not row.get("bucket_scores")]
    missing_context_rows = [
        row for row in all_rows if not row.get("previous_context") or not row.get("next_context")
    ]
    bucket_mismatches = [
        row for layer, rows in layers.items() for row in rows if row.get("bucket") != layer
    ]

    flag_sets = {
        "core_low_three_views": [
            row for row in layers["core"] if int(row.get("bucket_scores", {}).get("three_views", 0) or 0) < 10
        ],
        "background_high_three_views": [
            row for row in layers["background"] if int(row.get("bucket_scores", {}).get("three_views", 0) or 0) >= 15
        ],
        "style_high_three_views": [
            row for row in layers["style"] if int(row.get("bucket_scores", {}).get("three_views", 0) or 0) >= 15
        ],
        "counter_high_three_views": [
            row for row in layers["counter"] if int(row.get("bucket_scores", {}).get("three_views", 0) or 0) >= 15
        ],
        "copylike_or_long_burst": [
            row
            for row in all_rows
            if int(row.get("max_single_chars", 0) or 0) >= 180
            or float(row.get("avg_chars_per_message", 0) or 0) >= 45
        ],
        "very_large_burst": [
            row for row in all_rows if int(row.get("message_count", 0) or 0) >= 80
        ],
    }

    source_coverage = {
        layer: len({row.get("source_file", "") for row in rows})
        for layer, rows in layers.items()
    }
    chat_kind_counter = {
        layer: dict(Counter(str(row.get("chat_kind", "")) for row in rows))
        for layer, rows in layers.items()
    }

    core_ranked = sorted(
        layers["core"],
        key=lambda row: (
            int(row.get("bucket_scores", {}).get("three_views", 0) or 0),
            int(row.get("bucket_scores", {}).get("thinking", 0) or 0),
            int(row.get("message_count", 0) or 0),
        ),
        reverse=True,
    )
    top_core = [compact_episode(row) for row in core_ranked[: args.sample_size]]
    key_episode = by_episode.get("ep_010569", [])
    key_episode_rows = [compact_episode(row) for row in key_episode]
    key_rank = None
    for idx, row in enumerate(core_ranked, 1):
        if row.get("episode_id") == "ep_010569":
            key_rank = idx
            break

    lines: list[str] = []
    lines.append("# 蒸馏前语料审计")
    lines.append("")
    lines.append(f"- Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Source outputs: `{args.outputs_dir}`")
    lines.append("- Privacy posture: report keeps episode IDs and score metadata only; chat text stays in the external JSONL artifacts.")
    lines.append("")

    lines.append("## 结论")
    lines.append("")
    if duplicate_episode_ids or missing_score_rows or bucket_mismatches:
        lines.append("- Verdict: needs attention before final skill distillation.")
    else:
        lines.append("- Verdict: structurally ready for manual distillation sampling.")
    lines.append(f"- Layer counts: core {len(layers['core'])}; style {len(layers['style'])}; counter {len(layers['counter'])}; background {len(layers['background'])}.")
    lines.append(f"- Duplicate episode IDs across layer files: {len(duplicate_episode_ids)}.")
    lines.append(f"- Rows missing `bucket_scores`: {len(missing_score_rows)}.")
    lines.append(f"- Rows whose internal `bucket` mismatches file layer: {len(bucket_mismatches)}.")
    lines.append(f"- Rows with missing previous or next context: {len(missing_context_rows)}.")
    lines.append(f"- `ep_010569` placement: {'found' if key_episode else 'missing'}; score-resort core rank by three_views/thinking/message_count: {key_rank if key_rank else 'n/a'}.")
    lines.append("")

    lines.append("## Layer Summary")
    lines.append("")
    layer_rows = []
    for layer, rows in layers.items():
        layer_rows.append(
            {
                "layer": layer,
                "rows": len(rows),
                "source_files": source_coverage[layer],
                "chat_kind": chat_kind_counter[layer],
                "three_views_avg": score_summary(rows, "three_views")["avg"],
                "three_views_p90": score_summary(rows, "three_views")["p90"],
                "thinking_avg": score_summary(rows, "thinking")["avg"],
            }
        )
    lines.extend(render_table(layer_rows, ["layer", "rows", "source_files", "chat_kind", "three_views_avg", "three_views_p90", "thinking_avg"]))
    lines.append("")

    lines.append("## Score Distributions")
    lines.append("")
    for layer, rows in layers.items():
        lines.append(f"### {layer}")
        score_rows = []
        for key in SCORE_KEYS:
            item = score_summary(rows, key)
            item["score"] = key
            score_rows.append(item)
        lines.extend(render_table(score_rows, ["score", "min", "p50", "p90", "max", "avg"]))
        lines.append("")

    lines.append("## High Three-Views Core Sample")
    lines.append("")
    lines.extend(
        render_table(
            top_core,
            [
                "episode_id",
                "three_views",
                "worldview",
                "lifeview",
                "values",
                "thinking",
                "message_count",
                "avg_chars",
                "max_single_chars",
                "tags",
                "source_hash",
            ],
        )
    )
    lines.append("")

    lines.append("## Key Episode Check")
    lines.append("")
    if key_episode_rows:
        lines.extend(
            render_table(
                key_episode_rows,
                [
                    "episode_id",
                    "bucket",
                    "line_no",
                    "three_views",
                    "worldview",
                    "lifeview",
                    "values",
                    "thinking",
                    "message_count",
                    "tags",
                    "source_hash",
                ],
            )
        )
    else:
        lines.append("- `ep_010569` was not found in the audited layer files.")
    lines.append("")

    lines.append("## Boundary Flags")
    lines.append("")
    flag_rows = []
    for name, rows in flag_sets.items():
        by_layer = Counter(str(row.get("bucket", "")) for row in rows)
        flag_rows.append({"flag": name, "rows": len(rows), "by_layer": dict(by_layer)})
    lines.extend(render_table(flag_rows, ["flag", "rows", "by_layer"]))
    lines.append("")

    lines.append("## Flag Samples")
    lines.append("")
    for name, rows in flag_sets.items():
        lines.append(f"### {name}")
        sample = sorted(
            rows,
            key=lambda row: (
                int(row.get("bucket_scores", {}).get("three_views", 0) or 0),
                int(row.get("message_count", 0) or 0),
            ),
            reverse=True,
        )[: args.sample_size]
        if sample:
            lines.extend(
                render_table(
                    [compact_episode(row) for row in sample],
                    [
                        "episode_id",
                        "bucket",
                        "three_views",
                        "thinking",
                        "style",
                        "counter",
                        "message_count",
                        "avg_chars",
                        "max_single_chars",
                        "tags",
                        "source_hash",
                    ],
                )
            )
        else:
            lines.append("- None.")
        lines.append("")

    lines.append("## Suggested Manual Review Order")
    lines.append("")
    lines.append("1. Read the high three-views core sample first, especially worldview/lifeview/values-balanced episodes.")
    lines.append("2. Review `very_large_burst` and `copylike_or_long_burst` before using them as expression DNA.")
    lines.append("3. Inspect `background_high_three_views`; promote only if the self burst contains a stable value judgment rather than context.")
    lines.append("4. Use style episodes for rhythm and interaction mechanics, not for copying one-off words or private nicknames.")
    lines.append("5. Use counter episodes to define guardrails: uncertainty, over-force, conflict, and non-auto-send boundaries.")
    lines.append("")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
