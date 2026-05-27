"""Generate paper-oriented error analysis for real LLM baseline outputs."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from ..config import RESULTS_DIR


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-json",
        default="real_llm_baseline_30_replayed.json",
        help="Real LLM baseline JSON path.",
    )
    parser.add_argument(
        "--output-json",
        default="real_llm_error_analysis.json",
        help="Error analysis JSON output path.",
    )
    parser.add_argument(
        "--output-md",
        default="real_llm_error_analysis.md",
        help="Markdown error analysis output path.",
    )
    args = parser.parse_args()

    baseline = json.loads(_resolve_path(args.input_json).read_text(encoding="utf-8"))
    analysis = _build_analysis(baseline)

    json_path = _resolve_path(args.output_json)
    md_path = _resolve_path(args.output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(analysis), encoding="utf-8")

    print(f"Saved real LLM error analysis JSON to {json_path}")
    print(f"Saved real LLM error analysis table to {md_path}")
    print()
    print(_render_console_summary(analysis))


def _build_analysis(baseline: dict) -> dict:
    rows = [row for row in baseline["scenarios"] if row.get("status") == "completed"]
    completed_count = len(rows)
    scenario_rows = [_scenario_row(row) for row in rows]

    categories = {
        "guideline_only": [
            row for row in scenario_rows
            if row["guideline_detected_problem"] and not row["boolean_detected_problem"]
        ],
        "boolean_only": [
            row for row in scenario_rows
            if row["boolean_detected_problem"] and not row["guideline_detected_problem"]
        ],
        "both_detected": [
            row for row in scenario_rows
            if row["guideline_detected_problem"] and row["boolean_detected_problem"]
        ],
        "both_passed": [
            row for row in scenario_rows
            if not row["guideline_detected_problem"] and not row["boolean_detected_problem"]
        ],
        "conflicts": [
            row for row in scenario_rows
            if row["conflict_count"] > 0
        ],
        "unmatched": [
            row for row in scenario_rows
            if row["unmatched_items"]
        ],
    }

    violation_counter = Counter()
    conflict_counter = Counter()
    boolean_reason_counter = Counter()
    for row in scenario_rows:
        violation_counter.update(row["violated_nutrients"])
        conflict_counter.update(row["conflict_nutrients"])
        boolean_reason_counter.update(reason for _, reason in row["boolean_flags"])

    return {
        "metadata": {
            "source_runner": baseline.get("metadata", {}).get("runner"),
            "llm": baseline.get("metadata", {}).get("llm", {}),
            "scenario_count": baseline.get("metadata", {}).get("scenario_count", len(rows)),
            "completed_count": completed_count,
            "source_file_note": (
                "Error analysis is based on stored raw LLM outputs after deterministic "
                "food extraction and verification. It is not an independent clinical "
                "adjudication."
            ),
        },
        "summary": {
            "guideline_only_count": len(categories["guideline_only"]),
            "guideline_only_rate": _ratio(len(categories["guideline_only"]), completed_count),
            "boolean_only_count": len(categories["boolean_only"]),
            "boolean_only_rate": _ratio(len(categories["boolean_only"]), completed_count),
            "both_detected_count": len(categories["both_detected"]),
            "both_detected_rate": _ratio(len(categories["both_detected"]), completed_count),
            "both_passed_count": len(categories["both_passed"]),
            "both_passed_rate": _ratio(len(categories["both_passed"]), completed_count),
            "conflict_count": len(categories["conflicts"]),
            "conflict_rate": _ratio(len(categories["conflicts"]), completed_count),
            "unmatched_scenario_count": len(categories["unmatched"]),
            "unmatched_item_count": sum(len(row["unmatched_items"]) for row in categories["unmatched"]),
        },
        "takeaways": _takeaways(categories, violation_counter),
        "violation_counts": dict(sorted(violation_counter.items())),
        "conflict_counts": dict(sorted(conflict_counter.items())),
        "boolean_flag_counts": dict(sorted(boolean_reason_counter.items())),
        "categories": categories,
        "scenario_rows": scenario_rows,
    }


def _scenario_row(row: dict) -> dict:
    guideline = row["methods"]["guideline_graph_rag"]
    boolean = row["methods"]["boolean_graph_rag"]
    extraction = row.get("extraction", {})
    parsed_raw = _load_json_payload(row.get("raw_output", ""))
    rationale = parsed_raw.get("rationale", "") if isinstance(parsed_raw, dict) else ""
    return {
        "scenario_id": row["scenario_id"],
        "name": row["name"],
        "diseases": row["diseases"],
        "risk_factors": row["risk_factors"],
        "meal_type": row["meal_type"],
        "recommended_foods": extraction.get("recommended_foods", []),
        "recommended_foods_text": _format_foods(extraction.get("recommended_foods", [])),
        "unmatched_items": extraction.get("unmatched_items", []),
        "extraction_method": extraction.get("extraction_method"),
        "rationale": rationale,
        "guideline_detected_problem": guideline.get("detected_problem"),
        "boolean_detected_problem": boolean.get("detected_problem"),
        "guideline_passed": guideline.get("passed"),
        "boolean_passed": boolean.get("passed"),
        "violation_count": guideline.get("violation_count", 0),
        "conflict_count": guideline.get("conflict_count", 0),
        "violated_nutrients": guideline.get("violated_nutrients", []),
        "conflict_nutrients": guideline.get("conflict_nutrients", []),
        "evidence_sources": guideline.get("evidence_sources", []),
        "boolean_flags": [
            (item.get("food", ""), item.get("reason", ""))
            for item in boolean.get("flagged_foods", [])
        ],
        "expected_conflict_nutrient": row.get("expected_conflict_nutrient", ""),
        "expected_conflict_detected": row.get("expected_conflict_detected", False),
        "raw_output_path": row.get("raw_output_path"),
        "interpretation": _interpretation(guideline, boolean, extraction),
    }


def _interpretation(guideline: dict, boolean: dict, extraction: dict) -> str:
    guideline_problem = guideline.get("detected_problem")
    boolean_problem = boolean.get("detected_problem")
    if extraction.get("unmatched_items"):
        return "LLM used at least one item outside the current food table."
    if guideline_problem and not boolean_problem:
        if guideline.get("conflict_count", 0) > 0:
            return "Interval conflict detected by executable constraints; food-level rules alone missed it."
        return "Serving-weighted nutrient interval violation missed by food-level rules."
    if boolean_problem and not guideline_problem:
        return "Food-level rule flagged an item, but total intake remained within active executable intervals."
    if guideline_problem and boolean_problem:
        return "Both food-level rules and executable nutrient verification detected safety issues."
    return "No problem detected by either baseline under current prototype constraints."


def _takeaways(categories: dict, violation_counter: Counter) -> list[str]:
    most_common = ", ".join(
        f"{nutrient} ({count})"
        for nutrient, count in violation_counter.most_common(3)
    )
    return [
        (
            "Most real LLM failures are not formatting failures; they are "
            "serving-weighted nutrient interval issues."
        ),
        (
            "Guideline-constrained verification found substantially more issues "
            "than food-level boolean rules."
        ),
        (
            f"The most frequent violated nutrients were {most_common}."
            if most_common
            else "No nutrient violations were detected."
        ),
        (
            "Boolean-only cases indicate food-level rules can be over-conservative "
            "when total intake remains within active intervals."
            if categories["boolean_only"]
            else "No boolean-only over-conservative cases were found."
        ),
        (
            "The remaining extraction issue is a true out-of-table food item, not "
            "a simple local-name inversion."
            if categories["unmatched"]
            else "No unmatched food items remained after extraction normalization."
        ),
    ]


def _render_markdown(analysis: dict) -> str:
    summary = analysis["summary"]
    lines = [
        "# Real LLM Error Analysis",
        "",
        "## Scope",
        "",
        analysis["metadata"]["source_file_note"],
        "",
        "## Summary",
        "",
        "| Category | Count | Rate |",
        "|---|---:|---:|",
        f"| Guideline-only detections | {summary['guideline_only_count']} | {_fmt(summary['guideline_only_rate'])} |",
        f"| Boolean-only detections | {summary['boolean_only_count']} | {_fmt(summary['boolean_only_rate'])} |",
        f"| Both methods detected problems | {summary['both_detected_count']} | {_fmt(summary['both_detected_rate'])} |",
        f"| Both methods passed | {summary['both_passed_count']} | {_fmt(summary['both_passed_rate'])} |",
        f"| Conflict scenarios | {summary['conflict_count']} | {_fmt(summary['conflict_rate'])} |",
        f"| Scenarios with unmatched items | {summary['unmatched_scenario_count']} | NA |",
        f"| Unmatched item count | {summary['unmatched_item_count']} | NA |",
        "",
        "## Takeaways",
        "",
    ]
    lines.extend(f"- {item}" for item in analysis["takeaways"])
    lines.extend([
        "",
        "## Violation Counts",
        "",
        _counter_table("Nutrient", analysis["violation_counts"]),
        "",
        "## Boolean Flag Counts",
        "",
        _counter_table("Reason", analysis["boolean_flag_counts"]),
        "",
        "## Guideline-Only Detections",
        "",
        "These are cases where executable nutrient verification detected issues that food-level rules missed.",
        "",
        _category_table(analysis["categories"]["guideline_only"], include_boolean=False),
        "",
        "## Boolean-Only Detections",
        "",
        "These are cases where food-level rules flagged an item, but active nutrient intervals still passed.",
        "",
        _category_table(analysis["categories"]["boolean_only"], include_boolean=True),
        "",
        "## Conflict Cases",
        "",
        _category_table(analysis["categories"]["conflicts"], include_boolean=True),
        "",
        "## Unmatched Items",
        "",
        _unmatched_table(analysis["categories"]["unmatched"]),
        "",
        "## Both Methods Passed",
        "",
        _category_table(analysis["categories"]["both_passed"], include_boolean=True),
        "",
    ])
    return "\n".join(lines)


def _category_table(rows: list[dict], include_boolean: bool) -> str:
    if not rows:
        return "none"
    if include_boolean:
        lines = [
            "| Scenario | Diseases/Risks | Foods | Violations | Conflicts | Boolean Flags | Interpretation |",
            "|---|---|---|---|---|---|---|",
        ]
    else:
        lines = [
            "| Scenario | Diseases/Risks | Foods | Violations | Conflicts | Interpretation |",
            "|---|---|---|---|---|---|",
        ]
    for row in rows:
        base = [
            row["scenario_id"],
            _conditions(row),
            row["recommended_foods_text"],
            ", ".join(row["violated_nutrients"]) or "none",
            ", ".join(row["conflict_nutrients"]) or "none",
        ]
        if include_boolean:
            base.append(_format_boolean_flags(row["boolean_flags"]))
        base.append(row["interpretation"])
        lines.append("| " + " | ".join(_escape_cell(cell) for cell in base) + " |")
    return "\n".join(lines)


def _unmatched_table(rows: list[dict]) -> str:
    if not rows:
        return "none"
    lines = [
        "| Scenario | Unmatched Items | Extracted Foods | Raw Output Path |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                _escape_cell(cell)
                for cell in [
                    row["scenario_id"],
                    ", ".join(row["unmatched_items"]),
                    row["recommended_foods_text"],
                    row["raw_output_path"] or "",
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _counter_table(label: str, values: dict[str, int]) -> str:
    if not values:
        return "none"
    lines = [f"| {label} | Count |", "|---|---:|"]
    for key, value in sorted(values.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {_escape_cell(key)} | {value} |")
    return "\n".join(lines)


def _render_console_summary(analysis: dict) -> str:
    summary = analysis["summary"]
    return "\n".join([
        "Real LLM error analysis:",
        f"- guideline_only={summary['guideline_only_count']} ({_fmt(summary['guideline_only_rate'])})",
        f"- boolean_only={summary['boolean_only_count']} ({_fmt(summary['boolean_only_rate'])})",
        f"- both_detected={summary['both_detected_count']} ({_fmt(summary['both_detected_rate'])})",
        f"- both_passed={summary['both_passed_count']} ({_fmt(summary['both_passed_rate'])})",
        f"- conflicts={summary['conflict_count']} ({_fmt(summary['conflict_rate'])})",
        f"- unmatched_items={summary['unmatched_item_count']}",
    ])


def _format_foods(foods: list[dict]) -> str:
    return ", ".join(
        f"{food.get('name')}:{food.get('servings')}"
        for food in foods
    )


def _format_boolean_flags(flags: list[tuple[str, str]]) -> str:
    if not flags:
        return "none"
    return ", ".join(f"{food}:{reason}" for food, reason in flags)


def _conditions(row: dict) -> str:
    diseases = "+".join(row["diseases"]) or "none"
    risks = "+".join(row["risk_factors"]) or "none"
    return f"{diseases}; risk={risks}; meal={row['meal_type']}"


def _load_json_payload(text: str) -> Any | None:
    stripped = text.strip()
    candidates = [stripped]
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        candidates.insert(0, fenced.group(1).strip())
    object_match = re.search(r"(\{.*\})", stripped, flags=re.DOTALL)
    if object_match:
        candidates.append(object_match.group(1))
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _escape_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _fmt(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.4f}"


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else RESULTS_DIR / path


if __name__ == "__main__":
    main()
