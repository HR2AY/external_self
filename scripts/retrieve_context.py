#!/usr/bin/env python3
"""Read-only lexical and timeline retrieval for trajectory Personal Context."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parent.parent
BUNDLED_DATA_PATH = SKILL_ROOT / "assets" / "trajectory-app" / "data" / "places.json"
REQUIRED_FIELDS = {
    "id",
    "name",
    "city",
    "timePoint",
    "durationYears",
    "event",
    "longitude",
    "latitude",
}

STAGE_GROUPS = [
    ({"童年", "小时候", "儿童", "小学", "出生"}, {"童年", "小学", "出生"}),
    ({"中学", "初中", "高中", "学生", "校园"}, {"中学", "初中", "高中", "学校", "校园", "求学"}),
    ({"大学", "本科", "研究生", "求学", "校园"}, {"大学", "本科", "研究生", "求学", "学校", "校园"}),
    ({"工作", "职业", "上班", "公司"}, {"工作", "职业", "上班", "公司"}),
]


def resolve_data_path(explicit: str | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env_path = os.environ.get("TRAJECTORY_PERSONAL_CONTEXT")
    if env_path:
        candidates.append(Path(env_path))

    cwd = Path.cwd().resolve()
    candidates.extend(parent / "data" / "places.json" for parent in (cwd, *cwd.parents))
    candidates.append(BUNDLED_DATA_PATH)

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    checked = "\n".join(f"- {candidate}" for candidate in candidates)
    raise FileNotFoundError(f"Could not locate places.json. Checked:\n{checked}")


def load_nodes(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("FACT source must be a JSON array")
    nodes: list[dict[str, Any]] = []
    for index, node in enumerate(data):
        if not isinstance(node, dict):
            raise ValueError(f"Node {index} is not an object")
        missing = REQUIRED_FIELDS - node.keys()
        if missing:
            raise ValueError(f"Node {index} is missing fields: {', '.join(sorted(missing))}")
        nodes.append(node)
    return nodes


def normalized(value: Any) -> str:
    return re.sub(r"\s+", "", str(value).lower())


def query_terms(query: str) -> set[str]:
    segments = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", query.lower())
    terms: set[str] = set()
    for segment in segments:
        if re.fullmatch(r"[\u4e00-\u9fff]+", segment):
            terms.add(segment)
            for size in (2, 3, 4):
                terms.update(segment[i : i + size] for i in range(max(0, len(segment) - size + 1)))
        elif len(segment) > 1:
            terms.add(segment)
    return terms


def year_window(node: dict[str, Any]) -> tuple[int | None, float | None]:
    match = re.match(r"(\d{4})", str(node.get("timePoint", "")))
    if not match:
        return None, None
    start = int(match.group(1))
    try:
        duration = max(0.0, float(node.get("durationYears", 0)))
    except (TypeError, ValueError):
        duration = 0.0
    return start, start + duration


def score_node(node: dict[str, Any], query: str, terms: set[str], years: list[int]) -> tuple[float, list[str]]:
    query_text = normalized(query)
    name = normalized(node.get("name", ""))
    city = normalized(node.get("city", ""))
    event = normalized(node.get("event", ""))
    reasons: list[str] = []
    score = 0.0

    if name and name in query_text:
        score += 14
        reasons.append("地点名称直接匹配")
    if city and city in query_text:
        score += 11
        reasons.append("城市直接匹配")

    field_terms = {
        "地点名称": name,
        "城市": city,
        "事件": event,
    }
    for label, text in field_terms.items():
        overlaps = [term for term in terms if len(term) >= 2 and term in text]
        if overlaps:
            contribution = min(7, len(overlaps) * 1.5)
            score += contribution
            reasons.append(f"{label}关键词匹配: {', '.join(sorted(overlaps, key=len, reverse=True)[:3])}")

    start, end = year_window(node)
    if start is not None and end is not None:
        for year in years:
            if start <= year <= end:
                score += 12
                reasons.append(f"年份 {year} 落在节点时段 {start}–{end:g}")
            elif min(abs(year - start), abs(year - end)) <= 1:
                score += 5
                reasons.append(f"年份 {year} 接近节点时段 {start}–{end:g}")

    for query_words, event_words in STAGE_GROUPS:
        if any(word in query_text for word in query_words) and any(word in event for word in event_words):
            score += 7
            reasons.append("人生阶段匹配")
            break

    if node.get("event"):
        score += 0.25
    if node.get("city"):
        score += 0.25
    return score, reasons


def diverse_nodes(
    scored: list[tuple[float, dict[str, Any], list[str]]],
    limit: int,
    allow_unmatched: bool,
) -> list[tuple[float, dict[str, Any], list[str]]]:
    candidates = scored if allow_unmatched else [item for item in scored if item[0] > 0.5]
    ordered = sorted(candidates, key=lambda item: (item[0], str(item[1].get("timePoint", ""))), reverse=True)
    selected: list[tuple[float, dict[str, Any], list[str]]] = []
    seen_groups: set[str] = set()

    for item in ordered:
        city = normalized(item[1].get("city", ""))
        place_name = normalized(item[1].get("name", ""))
        group = city or place_name
        if group and group not in seen_groups:
            selected.append(item)
            seen_groups.add(group)
        if len(selected) >= limit:
            return selected

    for item in ordered:
        if item not in selected:
            selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="", help="Distilled conversation query")
    parser.add_argument("--data", help="Explicit path to the read-only places.json source")
    parser.add_argument("--mode", choices=("auto", "relevant", "diverse"), default="auto")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    try:
        data_path = resolve_data_path(args.data)
        nodes = load_nodes(data_path)
        limit = max(1, min(args.limit, 5))
        terms = query_terms(args.query)
        years = [int(value) for value in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", args.query)]
        scored = []
        for node in nodes:
            score, reasons = score_node(node, args.query, terms, years)
            scored.append((score, node, reasons))

        if args.mode == "diverse":
            selected = diverse_nodes(scored, limit, allow_unmatched=not args.query.strip())
            used_mode = "diverse"
        else:
            relevant = sorted((item for item in scored if item[0] > 0.5), key=lambda item: item[0], reverse=True)
            if relevant:
                selected = relevant[:limit]
                used_mode = "relevant"
            elif args.mode == "auto":
                selected = []
                used_mode = "no-match"
            else:
                selected = []
                used_mode = "relevant"

        output = {
            "source": str(data_path),
            "source_class": "FACT",
            "read_only": True,
            "node_count": len(nodes),
            "trajectory_empty": len(nodes) == 0,
            "query": args.query,
            "mode": used_mode,
            "matches": [
                {
                    "score": round(score, 2),
                    "reasons": reasons or ["用于跨时期多节点比较"],
                    "node": node,
                }
                for score, node, reasons in selected
            ],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error), "read_only": True}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
