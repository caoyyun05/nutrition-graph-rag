"""Generate first-pass comparison metrics from baseline results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import RESULTS_DIR


METHOD_LABELS = {
    "pure_llm": "Pure LLM",
    "pure_kg": "Pure KG",
    "boolean_graph_rag": "Boolean Graph-RAG",
    "guideline_graph_rag": "Guideline-Constrained Graph-RAG",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-json",
        default="baseline_comparison.json",
        help="Baseline comparison JSON path.",
    )
    parser.add_argument(
        "--output-json",
        default="comparison_metrics.json",
        help="Metrics JSON output path.",
    )
    parser.add_argument(
        "--output-md",
        default="comparison_metrics.md",
        help="Markdown table output path.",
    )
    args = parser.parse_args()

    comparison = json.loads(_resolve_path(args.input_json).read_text(encoding="utf-8"))
    metrics = _compute_metrics(comparison)

    json_path = _resolve_path(args.output_json)
    md_path = _resolve_path(args.output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(metrics), encoding="utf-8")

    print(f"Saved metrics JSON to {json_path}")
    print(f"Saved metrics table to {md_path}")
    print()
    print(_render_console_summary(metrics))


def _compute_metrics(comparison: dict) -> dict:
    scenarios = comparison["scenarios"]
    scenario_count = len(scenarios)
    methods = comparison["metadata"]["methods"]
    unsafe_scenarios = [
        row for row in scenarios
        if row["methods"]["guideline_graph_rag"]["detected_problem"]
    ]
    unsafe_count = len(unsafe_scenarios)
    conflict_scenarios = [
        row for row in scenarios
        if row["methods"]["guideline_graph_rag"]["conflict_count"] > 0
    ]
    expected_conflict_scenarios = [
        row for row in scenarios
        if row["expected_conflict_nutrient"]
    ]

    method_rows = []
    for method in methods:
        method_rows.append(_method_metrics(method, scenarios, unsafe_scenarios))

    proposed = next(row for row in method_rows if row["method"] == "guideline_graph_rag")
    boolean = next(row for row in method_rows if row["method"] == "boolean_graph_rag")

    return {
        "metadata": {
            "scenario_count": scenario_count,
            "unsafe_reference_count": unsafe_count,
            "safe_reference_count": scenario_count - unsafe_count,
            "conflict_reference_count": len(conflict_scenarios),
            "expected_conflict_count": len(expected_conflict_scenarios),
            "note": (
                "First-pass metrics use the guideline-constrained method as the "
                "reference verifier because independent clinical labels are not "
                "yet available."
            ),
        },
        "metric_definitions": _metric_definitions(),
        "method_metrics": method_rows,
        "conflict_metrics": {
            "expected_conflict_detection_rate": _ratio(
                sum(1 for row in expected_conflict_scenarios if row["expected_conflict_detected"]),
                len(expected_conflict_scenarios),
            ),
            "expected_conflicts_detected": sum(
                1 for row in expected_conflict_scenarios if row["expected_conflict_detected"]
            ),
            "expected_conflict_count": len(expected_conflict_scenarios),
            "conflict_scenario_ids": [row["scenario_id"] for row in conflict_scenarios],
        },
        "delta_vs_boolean": {
            "additional_problem_detections": (
                proposed["problem_detected_count"] - boolean["problem_detected_count"]
            ),
            "additional_problem_detection_rate": round(
                proposed["problem_detection_rate"] - boolean["problem_detection_rate"],
                4,
            ),
        },
        "scenario_outcomes": [
            {
                "scenario_id": row["scenario_id"],
                "name": row["name"],
                "reference_unsafe": row["methods"]["guideline_graph_rag"]["detected_problem"],
                "guideline_passed": row["methods"]["guideline_graph_rag"]["passed"],
                "violation_count": row["methods"]["guideline_graph_rag"]["violation_count"],
                "conflict_count": row["methods"]["guideline_graph_rag"]["conflict_count"],
                "boolean_detected_problem": row["methods"]["boolean_graph_rag"]["detected_problem"],
                "expected_conflict_nutrient": row["expected_conflict_nutrient"],
                "expected_conflict_detected": row["expected_conflict_detected"],
            }
            for row in scenarios
        ],
    }


def _method_metrics(method: str, scenarios: list[dict], unsafe_scenarios: list[dict]) -> dict:
    scenario_count = len(scenarios)
    unsafe_count = len(unsafe_scenarios)
    method_results = [row["methods"][method] for row in scenarios]
    problem_detected_count = sum(1 for result in method_results if result.get("detected_problem"))
    passed_count = sum(1 for result in method_results if result.get("passed") is True)
    failed_count = sum(1 for result in method_results if result.get("passed") is False)
    unknown_count = sum(1 for result in method_results if result.get("passed") is None)

    unsafe_detected = sum(
        1
        for row in unsafe_scenarios
        if row["methods"][method].get("detected_problem")
    )

    return {
        "method": method,
        "label": METHOD_LABELS.get(method, method),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "unknown_count": unknown_count,
        "problem_detected_count": problem_detected_count,
        "pass_rate": _ratio(passed_count, scenario_count),
        "problem_detection_rate": _ratio(problem_detected_count, scenario_count),
        "unsafe_detection_rate": _ratio(unsafe_detected, unsafe_count),
        "deterministic_verification": any(
            result.get("deterministic_verification") for result in method_results
        ),
    }


def _metric_definitions() -> dict:
    return {
        "pass_rate": "passed_count / total_scenarios",
        "problem_detection_rate": "problem_detected_count / total_scenarios",
        "unsafe_detection_rate": (
            "problem detections among scenarios marked unsafe by the "
            "guideline-constrained verifier / guideline-unsafe scenarios"
        ),
        "expected_conflict_detection_rate": (
            "expected comorbidity conflict scenarios detected / expected conflict scenarios"
        ),
        "important_limit": (
            "These are first-pass engineering metrics. They use the proposed "
            "guideline-constrained verifier as the reference because independent "
            "expert labels are not yet available."
        ),
    }


def _render_markdown(metrics: dict) -> str:
    lines = [
        "# Comparison Metrics",
        "",
        "Generated from `results_v2/baseline_comparison.json`.",
        "",
        "## Important Limitation",
        "",
        metrics["metric_definitions"]["important_limit"],
        "",
        "## Method-Level Metrics",
        "",
        "| Method | Passed | Failed | Unknown | Pass Rate | Problem Detection Rate | Unsafe Detection Rate | Deterministic Verification |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in metrics["method_metrics"]:
        lines.append(
            "| "
            f"{row['label']} | "
            f"{row['passed_count']} | "
            f"{row['failed_count']} | "
            f"{row['unknown_count']} | "
            f"{_fmt(row['pass_rate'])} | "
            f"{_fmt(row['problem_detection_rate'])} | "
            f"{_fmt(row['unsafe_detection_rate'])} | "
            f"{row['deterministic_verification']} |"
        )

    conflict = metrics["conflict_metrics"]
    delta = metrics["delta_vs_boolean"]
    lines.extend([
        "",
        "## Conflict Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Expected conflict scenarios | {conflict['expected_conflict_count']} |",
        f"| Expected conflicts detected | {conflict['expected_conflicts_detected']} |",
        f"| Expected conflict detection rate | {_fmt(conflict['expected_conflict_detection_rate'])} |",
        "",
        "Conflict scenario IDs:",
        "",
        ", ".join(conflict["conflict_scenario_ids"]) or "none",
        "",
        "## Delta vs Boolean Graph-RAG",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Additional problem detections | {delta['additional_problem_detections']} |",
        f"| Additional problem detection rate | {_fmt(delta['additional_problem_detection_rate'])} |",
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
    lines = ["Method metrics:"]
    for row in metrics["method_metrics"]:
        lines.append(
            f"- {row['method']}: "
            f"problem_detection_rate={_fmt(row['problem_detection_rate'])}, "
            f"unsafe_detection_rate={_fmt(row['unsafe_detection_rate'])}"
        )
    lines.append(
        "Expected conflict detection rate: "
        f"{_fmt(metrics['conflict_metrics']['expected_conflict_detection_rate'])}"
    )
    return "\n".join(lines)


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
