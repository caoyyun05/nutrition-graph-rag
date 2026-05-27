"""Summarize multi-model repeated LLM audit outputs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from ..config import RESULTS_DIR


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="multi_llm_audit_usda_pilot")
    parser.add_argument("--output-json", default="multi_llm_audit_usda_pilot_metrics.json")
    parser.add_argument("--output-md", default="multi_llm_audit_usda_pilot_metrics.md")
    args = parser.parse_args()

    input_dir = _resolve_results_path(args.input_dir)
    runs = _load_completed_runs(input_dir)
    metrics = _compute_metrics(runs)

    json_path = _resolve_results_path(args.output_json)
    md_path = _resolve_results_path(args.output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(metrics), encoding="utf-8")
    print(f"Saved multi-LLM metrics JSON to {json_path}")
    print(f"Saved multi-LLM metrics table to {md_path}")


def _load_completed_runs(input_dir: Path) -> list[dict]:
    manifest_path = input_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    runs = []
    for run in manifest["runs"]:
        path = Path(run["output_json"])
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("metadata", {}).get("dry_run"):
            continue
        runs.append({"manifest": run, "data": data})
    return runs


def _compute_metrics(runs: list[dict]) -> dict:
    model_rows = []
    scenario_variability = []
    by_model: dict[tuple[str, str], list[dict]] = defaultdict(list)
    by_scenario_model: dict[tuple[str, str, str], list[dict]] = defaultdict(list)

    for run in runs:
        llm = run["data"].get("metadata", {}).get("llm", {})
        provider = llm.get("provider", run["manifest"].get("provider", "unknown"))
        model = llm.get("model", run["manifest"].get("model", "unknown"))
        by_model[(provider, model)].append(run)
        for row in run["data"].get("scenarios", []):
            if row.get("status") == "completed":
                by_scenario_model[(provider, model, row["scenario_id"])].append(row)

    for (provider, model), model_runs in sorted(by_model.items()):
        completed_rows = [
            row
            for run in model_runs
            for row in run["data"].get("scenarios", [])
            if row.get("status") == "completed"
        ]
        model_rows.append(_model_metrics(provider, model, model_runs, completed_rows))

    for (provider, model, scenario_id), rows in sorted(by_scenario_model.items()):
        if len(rows) < 2:
            continue
        signatures = {_food_signature(row) for row in rows}
        problem_values = {
            bool(row["methods"]["guideline_graph_rag"].get("detected_problem"))
            for row in rows
        }
        scenario_variability.append(
            {
                "provider": provider,
                "model": model,
                "scenario_id": scenario_id,
                "repeat_count": len(rows),
                "unique_recommendation_count": len(signatures),
                "recommendation_varied": len(signatures) > 1,
                "verification_outcome_varied": len(problem_values) > 1,
            }
        )

    return {
        "metadata": {
            "run_count": len(runs),
            "model_count": len(model_rows),
            "note": (
                "Metrics summarize completed API-backed multi-model repeated LLM "
                "recommendation audits. Dry-run prompt-only runs are ignored."
            ),
        },
        "model_metrics": model_rows,
        "variability_metrics": {
            "scenario_model_cells": len(scenario_variability),
            "recommendation_varied_count": sum(
                1 for row in scenario_variability if row["recommendation_varied"]
            ),
            "verification_outcome_varied_count": sum(
                1 for row in scenario_variability if row["verification_outcome_varied"]
            ),
            "rows": scenario_variability,
        },
    }


def _model_metrics(provider: str, model: str, runs: list[dict], rows: list[dict]) -> dict:
    completed = len(rows)
    json_count = sum(
        1
        for row in rows
        if row.get("extraction", {}).get("extraction_method") == "json"
    )
    zero_extraction = sum(
        1
        for row in rows
        if not row.get("extraction", {}).get("recommended_foods", [])
    )
    unmatched = sum(
        len(row.get("extraction", {}).get("unmatched_items", []))
        for row in rows
    )
    guideline_problem = sum(
        1
        for row in rows
        if row["methods"]["guideline_graph_rag"].get("detected_problem")
    )
    hard_safety_issue = sum(
        1
        for row in rows
        if row["methods"]["guideline_graph_rag"].get("has_hard_safety_issue")
    )
    soft_target_miss = sum(
        1
        for row in rows
        if row["methods"]["guideline_graph_rag"].get("has_soft_target_miss")
    )
    boolean_problem = sum(
        1
        for row in rows
        if row["methods"]["boolean_graph_rag"].get("detected_problem")
    )
    expected_conflicts = [
        row for row in rows if row.get("expected_conflict_nutrient")
    ]
    expected_conflict_detected = sum(
        1 for row in expected_conflicts if row.get("expected_conflict_detected")
    )
    return {
        "provider": provider,
        "model": model,
        "run_count": len(runs),
        "completed_count": completed,
        "json_extraction_rate": _ratio(json_count, completed),
        "zero_extraction_rate": _ratio(zero_extraction, completed),
        "unmatched_item_count": unmatched,
        "guideline_problem_rate": _ratio(guideline_problem, completed),
        "hard_safety_issue_rate": _ratio(hard_safety_issue, completed),
        "soft_target_miss_rate": _ratio(soft_target_miss, completed),
        "boolean_problem_rate": _ratio(boolean_problem, completed),
        "expected_conflict_detection_rate": _ratio(
            expected_conflict_detected,
            len(expected_conflicts),
        ),
    }


def _food_signature(row: dict) -> str:
    foods = row.get("extraction", {}).get("recommended_foods", [])
    pairs = [
        (item.get("name", ""), float(item.get("servings", 0)))
        for item in foods
    ]
    return json.dumps(sorted(pairs), ensure_ascii=False)


def _render_markdown(metrics: dict) -> str:
    lines = [
        "# Multi-LLM Recommendation Audit Metrics",
        "",
        "## Model-Level Metrics",
        "",
        "| Provider | Model | Runs | Completed | JSON extraction | Zero extraction | Unmatched items | Any verifier finding | Hard safety issue | Soft target miss | Boolean problem rate | Expected conflict detection |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics["model_metrics"]:
        lines.append(
            "| "
            f"{row['provider']} | "
            f"{row['model']} | "
            f"{row['run_count']} | "
            f"{row['completed_count']} | "
            f"{_fmt(row['json_extraction_rate'])} | "
            f"{_fmt(row['zero_extraction_rate'])} | "
            f"{row['unmatched_item_count']} | "
            f"{_fmt(row['guideline_problem_rate'])} | "
            f"{_fmt(row['hard_safety_issue_rate'])} | "
            f"{_fmt(row['soft_target_miss_rate'])} | "
            f"{_fmt(row['boolean_problem_rate'])} | "
            f"{_fmt(row['expected_conflict_detection_rate'])} |"
        )

    variability = metrics["variability_metrics"]
    lines.extend(
        [
            "",
            "## Repeated-Generation Variability",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Scenario-model cells with repeated outputs | {variability['scenario_model_cells']} |",
            f"| Cells with varied recommendations | {variability['recommendation_varied_count']} |",
            f"| Cells with varied verification outcomes | {variability['verification_outcome_varied_count']} |",
            "",
            "## Scenario-Level Variability",
            "",
            "| Provider | Model | Scenario | Repeats | Unique recommendations | Recommendation varied | Verification outcome varied |",
            "|---|---|---|---:|---:|---|---|",
        ]
    )
    for row in variability["rows"]:
        lines.append(
            "| "
            f"{row['provider']} | "
            f"{row['model']} | "
            f"{row['scenario_id']} | "
            f"{row['repeat_count']} | "
            f"{row['unique_recommendation_count']} | "
            f"{row['recommendation_varied']} | "
            f"{row['verification_outcome_varied']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _fmt(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.4f}"


def _resolve_results_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else RESULTS_DIR / path


if __name__ == "__main__":
    main()
