#!/usr/bin/env python
"""Audit aggregate dyadic profile output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_PRIVATE_PROFILES = {
    "叶莎莎 / 小lisa": 50000,
    "刘智": 10000,
    "Qiuliang": 5000,
    "妈": 1000,
    "老方": 100,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profiles",
        type=Path,
        default=Path("runtime/dyadic-profiles/profiles.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.profiles.read_text(encoding="utf-8"))
    profiles = payload.get("profiles") or []
    by_name = {item["canonical_name"]: item for item in profiles}
    failures: list[str] = []

    if payload.get("source_manifest", {}).get("privacy_mode") != "aggregate_only_no_raw_text":
        failures.append("privacy mode missing")
    if not payload.get("global_profile"):
        failures.append("global profile missing")

    forbidden_keys = {"content", "raw_text", "message_text", "dialogue"}
    serialized_keys: set[str] = set()

    def collect_keys(value):
        if isinstance(value, dict):
            serialized_keys.update(value.keys())
            for child in value.values():
                collect_keys(child)
        elif isinstance(value, list):
            for child in value:
                collect_keys(child)

    collect_keys(payload)
    leaked = forbidden_keys & serialized_keys
    if leaked:
        failures.append("forbidden raw-text keys: " + ", ".join(sorted(leaked)))

    for name, minimum_outgoing in REQUIRED_PRIVATE_PROFILES.items():
        profile = by_name.get(name)
        if not profile:
            failures.append(f"missing profile: {name}")
            continue
        outgoing = profile.get("evidence", {}).get("private_outgoing_count", 0)
        if outgoing < minimum_outgoing:
            failures.append(f"private outgoing too low for {name}: {outgoing}")
        if not profile.get("relative_to_global"):
            failures.append(f"global contrast missing for {name}")

    spouse = by_name.get("叶莎莎 / 小lisa") or {}
    spouse_aliases = set(spouse.get("aliases") or [])
    for expected_alias in ("1469", "葉莎莎Lisa🐈", "小lisa🐰"):
        if expected_alias not in spouse_aliases:
            failures.append(f"spouse alias missing: {expected_alias}")
    for duplicate in ("葉莎莎Lisa🐱", "小lisa🐰"):
        if duplicate in by_name:
            failures.append(f"unmerged duplicate profile: {duplicate}")

    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    levels: dict[str, int] = {}
    for profile in profiles:
        level = profile.get("confidence", {}).get("level", "unknown")
        levels[level] = levels.get(level, 0) + 1
    print(f"PASS profiles={len(profiles)} levels={levels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

