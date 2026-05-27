"""Generate metrics from API-backed real LLM baseline results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import RESULTS_DIR


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-json",
        default="real_llm_baseline.json",
        help="Real LLM baseline JSON path.",
    )
    parser.add_argument(
        "--output-json",
        default="real_llm_metrics.json",
        help="Metrics JSON output path.",
    )
    parser.add_argument(
        "--output-md",
        default="real_llm_metrics.md",
        help="Markdown metrics output path.",
    )
    args = parser.parse_args()

    baseline = json.loads(_resolve_path(args.input_json).read_text(encoding="utf-8"))
    metrics = _compute_metrics(baseline)

    json_path = _resolve_path(args.output_json)
    md_path = _resolve_path(args.output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(metrics), encoding="utf-8")

    print(f"Saved real LLM metrics JSON to {json_path}")
    print(f"Saved real LLM metrics table to {md_path}")
    print()
    print(_render_console_summary(metrics))


def _compute_metrics(baseline: dict) -> dict:
    rows = baseline["scenarios"]
    completed = [row for row in rows if row.get("status") == "completed"]
    completed_count = len(completed)
    dry_run_count = sum(1 for row in rows if row.get("status") == "dry_run")

    extracted_counts = [
        len(row.get("extraction", {}).get("recommended_foods", []))
        for row in completed
    ]
    json_extraction_count = sum(
        1
        for row in completed
        if row.get("extraction", {}).get("extraction_method") == "json"
    )
    zero_extraction_count = sum(1 for count in extracted_counts if count == 0)
    unmatched_item_count = sum(
        len(row.get("extraction", {}).get("unmatched_items", []))
        for row in completed
    )

    guideline_problem_rows = [
        row for row in completed
        if row["methods"]["guideline_graph_rag"].get("detected_problem")
    ]
    boolean_problem_rows = [
        row for row in completed
        if row["methods"]["boolean_graph_rag"].get("detected_problem")
    ]
    guideline_only_rows = [
        row for row in completed
        if (
            row["methods"]["guideline_graph_rag"].get("detected_problem")
            and not row["methods"]["boolean_graph_rag"].get("detected_problem")
        )
    ]
    boolean_only_rows = [
        row for row in completed
        if (
            row["methods"]["boolean_graph_rag"].get("detected_problem")
            and not row["methods"]["guideline_graph_rag"].get("detected_problem")
        )
    ]
    both_problem_rows = [
        row for row in completed
        if (
            row["methods"]["guideline_graph_rag"].get("detected_problem")
            and row["methods"]["boolean_graph_rag"].get("detected_problem")
        )
    ]
    expected_conflict_rows = [
        row for row in completed
        if row.get("expected_conflict_nutrient")
    ]
    expected_conflicts_detected = sum(
        1 for row in expected_conflict_rows if row.get("expected_conflict_detected")
    )
    conflict_rows = [
        row for row in completed
        if row["methods"]["guideline_graph_rag"].get("conflict_count", 0) > 0
    ]

    return {
        "metadata": {
            "source_runner": baseline.get("metadata", {}).get("runner"),
            "llm": baseline.get("metadata", {}).get("llm", {}),
            "scenario_count": len(rows),
            "completed_count": completed_count,
            "dry_run_count": dry_run_count,
            "note": (
                "Metrics are computed from real LLM outputs after deterministic "
                "food extraction and guideline-constrained verification."
            ),
        },
        "metric_definitions": _metric_definitions(),
        "extraction_metrics": {
            "json_extraction_count": json_extraction_count,
            "json_extraction_rate": _ratio(json_extraction_count, completed_count),
            "average_extracted_food_count": (
                round(sum(extracted_counts) / completed_count, 4)
                if completed_count
                else None
            ),
            "zero_extraction_count": zero_extraction_count,
            "zero_extraction_rate": _ratio(zero_extraction_count, completed_count),
            "unmatched_item_count": unmatched_item_count,
        },
        "safety_metrics": {
            "guideline_problem_count": len(guideline_problem_rows),
            "guideline_problem_rate": _ratio(len(guideline_problem_rows), completed_count),
            "boolean_problem_count": len(boolean_problem_rows),
            "boolean_problem_rate": _ratio(len(boolean_problem_rows), completed_count),
            "guideline_only_problem_count": len(guideline_only_rows),
            "guideline_only_problem_rate": _ratio(len(guideline_only_rows), completed_count),
            "boolean_only_problem_count": len(boolean_only_rows),
            "boolean_only_problem_rate": _ratio(len(boolean_only_rows), completed_count),
            "both_problem_count": len(both_problem_rows),
            "both_problem_rate": _ratio(len(both_problem_rows), completed_count),
            "additional_guideline_detections_vs_boolean": (
                len(guideline_problem_rows) - len(boolean_problem_rows)
            ),
            "additional_guideline_detection_rate_vs_boolean": _subtract_ratios(
                _ratio(len(guideline_problem_rows), completed_count),
                _ratio(len(boolean_problem_rows), completed_count),
            ),
        },
        "conflict_metrics": {
            "expected_conflict_count": len(expected_conflict_rows),
            "expected_conflicts_detected": expected_conflicts_detected,
            "expected_conflict_detection_rate": _ratio(
                expected_conflicts_detected,
                len(expected_conflict_rows),
            ),
            "guideline_conflict_count": len(conflict_rows),
            "guideline_conflict_rate": _ratio(len(conflict_rows), completed_count),
            "conflict_scenario_ids": [row["scenario_id"] for row in conflict_rows],
        },
        "scenario_outcomes": [_scenario_outcome(row) for row in completed],
    }


def _scenario_outcome(row: dict) -> dict:
    guideline = row["methods"]["guideline_graph_rag"]
    boolean = row["methods"]["boolean_graph_rag"]
    extraction = row.get("extraction", {})
    return {
        "scenario_id": row["scenario_id"],
        "name": row["name"],
        "diseases": row["diseases"],
        "risk_factors": row["risk_factors"],
        "extraction_method": extraction.get("extraction_method"),
        "extracted_food_count": len(extraction.get("recommended_foods", [])),
        "unmatched_items": extraction.get("unmatched_items", []),
        "recommended_foods": extraction.get("recommended_foods", []),
        "guideline_detected_problem": guideline.get("detected_problem"),
        "boolean_detected_problem": boolean.get("detected_problem"),
        "guideline_passed": guideline.get("passed"),
        "violation_count": guideline.get("violation_count"),
        "conflict_count": guideline.get("conflict_count"),
        "violated_nutrients": guideline.get("violated_nutrients", []),
        "conflict_nutrients": guideline.get("conflict_nutrients", []),
        "expected_conflict_nutrient": row.get("expected_conflict_nutrient", ""),
        "expected_conflict_detected": row.get("expected_conflict_detected", False),
        "raw_output_path": row.get("raw_output_path"),
    }


def _metric_definitions() -> dict:
    return {
        "json_extraction_rate": "completed scenarios with JSON extraction / completed scenarios",
        "zero_extraction_rate": "completed scenarios with zero extracted foods / completed scenarios",
        "guideline_problem_rate": "LLM recommendations flagged by guideline verifier / completed scenarios",
        "boolean_problem_rate": "LLM recommendations flagged by food-level boolean baseline / completed scenarios",
        "guideline_only_problem_rate": (
            "LLM recommendations flagged by guideline verifier but not by boolean baseline / "
            "completed scenarios"
        ),
        "expected_conflict_detection_rate": (
            "expected conflict scenarios detected by guideline verifier / expected conflict scenarios"
        ),
        "important_limit": (
            "These metrics evaluate generated recommendations against the current "
            "prototype verifier. Independent expert labels are still needed for "
            "final publication claims."
        ),
    }


def _render_markdown(metrics: dict) -> str:
    extraction = metrics["extraction_metrics"]
    safety = metrics["safety_metrics"]
    conflict = metrics["conflict_metrics"]
    lines = [
        "# Real LLM Baseline Metrics",
        "",
        "## Important Limitation",
        "",
        metrics["metric_definitions"]["important_limit"],
        "",
        "## Run Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Scenarios | {metrics['metadata']['scenario_count']} |",
        f"| Completed | {metrics['metadata']['completed_count']} |",
        f"| Dry runs | {metrics['metadata']['dry_run_count']} |",
        f"| LLM provider | {metrics['metadata']['llm'].get('provider', 'NA')} |",
        f"| LLM model | {metrics['metadata']['llm'].get('model', 'NA')} |",
        "",
        "## Extraction Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| JSON extraction count | {extraction['json_extraction_count']} |",
        f"| JSON extraction rate | {_fmt(extraction['json_extraction_rate'])} |",
        f"| Average extracted food count | {_fmt(extraction['average_extracted_food_count'])} |",
        f"| Zero extraction count | {extraction['zero_extraction_count']} |",
        f"| Zero extraction rate | {_fmt(extraction['zero_extraction_rate'])} |",
        f"| Unmatched item count | {extraction['unmatched_item_count']} |",
        "",
        "## Safety Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Guideline problem count | {safety['guideline_problem_count']} |",
        f"| Guideline problem rate | {_fmt(safety['guideline_problem_rate'])} |",
        f"| Boolean problem count | {safety['boolean_problem_count']} |",
        f"| Boolean problem rate | {_fmt(safety['boolean_problem_rate'])} |",
        f"| Guideline-only problem count | {safety['guideline_only_problem_count']} |",
        f"| Guideline-only problem rate | {_fmt(safety['guideline_only_problem_rate'])} |",
        f"| Boolean-only problem count | {safety['boolean_only_problem_count']} |",
        f"| Boolean-only problem rate | {_fmt(safety['boolean_only_problem_rate'])} |",
        f"| Additional guideline detections vs boolean | {safety['additional_guideline_detections_vs_boolean']} |",
        f"| Additional guideline detection rate vs boolean | {_fmt(safety['additional_guideline_detection_rate_vs_boolean'])} |",
        "",
        "## Conflict Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Expected conflict scenarios | {conflict['expected_conflict_count']} |",
        f"| Expected conflicts detected | {conflict['expected_conflicts_detected']} |",
        f"| Expected conflict detection rate | {_fmt(conflict['expected_conflict_detection_rate'])} |",
        f"| Guideline conflict count | {conflict['guideline_conflict_count']} |",
        f"| Guideline conflict rate | {_fmt(conflict['guideline_conflict_rate'])} |",
        "",
        "Conflict scenario IDs:",
        "",
        ", ".join(conflict["conflict_scenario_ids"]) or "none",
        "",
        "## Scenario Outcomes",
        "",
        "| Scenario | Extracted Foods | Guideline Problem | Boolean Problem | Violations | Conflicts | Violated Nutrients | Conflict Nutrients |",
        "|---|---:|---|---|---:|---:|---|---|",
    ]
    for row in metrics["scenario_outcomes"]:
        lines.append(
            "| "
            f"{row['scenario_id']} | "
            f"{row['extracted_food_count']} | "
            f"{row['guideline_detected_problem']} | "
            f"{row['boolean_detected_problem']} | "
            f"{row['violation_count']} | "
            f"{row['conflict_count']} | "
            f"{', '.join(row['violated_nutrients']) or 'none'} | "
            f"{', '.join(row['conflict_nutrients']) or 'none'} |"
        )

    lines.extend([
        "",
        "## Metric Definitions",
        "",
    ])
    for name, definition in metrics["metric_definitions"].items():
        if name != "important_limit":
            lines.append(f"- `{name}`: {definition}")
    lines.append("")
    return "\n".join(lines)


def _render_console_summary(metrics: dict) -> str:
    extraction = metrics["extraction_metrics"]
    safety = metrics["safety_metrics"]
    conflict = metrics["conflict_metrics"]
    return "\n".join([
        "Real LLM metrics:",
        f"- completed={metrics['metadata']['completed_count']}",
        f"- json_extraction_rate={_fmt(extraction['json_extraction_rate'])}",
        f"- average_extracted_food_count={_fmt(extraction['average_extracted_food_count'])}",
        f"- guideline_problem_rate={_fmt(safety['guideline_problem_rate'])}",
        f"- boolean_problem_rate={_fmt(safety['boolean_problem_rate'])}",
        f"- guideline_only_problem_rate={_fmt(safety['guideline_only_problem_rate'])}",
        f"- expected_conflict_detection_rate={_fmt(conflict['expected_conflict_detection_rate'])}",
    ])


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _subtract_ratios(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(left - right, 4)


def _fmt(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.4f}"


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else RESULTS_DIR / path


if __name__ == "__main__":
    main()
