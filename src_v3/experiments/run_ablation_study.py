"""Run module-level ablations for the v2 guideline verifier."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from ..config import DATA_DIR, RESULTS_DIR
from ..conflict_detector import detect_interval_conflicts
from ..csv_loader import load_constraints, load_foods, select_active_constraints
from ..evidence_report import build_evidence_report
from ..interval_verifier import verify_nutrient_ranges
from ..models import NutrientConstraint
from ..nutrient_calculator import compute_nutrient_totals
from .scenarios import TestScenario, load_scenarios


VARIANTS = [
    "full_system",
    "without_nutrient_range",
    "without_conflict_detection",
    "without_evidence_provenance",
    "rda_only_constraints",
]

VARIANT_LABELS = {
    "full_system": "Full system",
    "without_nutrient_range": "w/o nutrient-range verification",
    "without_conflict_detection": "w/o conflict detection",
    "without_evidence_provenance": "w/o evidence provenance",
    "rda_only_constraints": "RDA-only constraints",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-json",
        default="ablation_study_90.json",
        help="Path for saving structured ablation results.",
    )
    parser.add_argument(
        "--output-md",
        default="ablation_study_90.md",
        help="Path for saving the markdown ablation table.",
    )
    parser.add_argument("--foods-csv", default=str(DATA_DIR / "foods_extended.csv"))
    parser.add_argument("--constraints-csv", default=str(DATA_DIR / "nutrient_constraints.csv"))
    parser.add_argument("--scenarios-csv", default=str(DATA_DIR / "test_scenarios.csv"))
    args = parser.parse_args()

    foods = load_foods(Path(args.foods_csv))
    constraints = load_constraints(Path(args.constraints_csv))
    scenarios = load_scenarios(Path(args.scenarios_csv))

    rows = [_evaluate_scenario(scenario, foods, constraints) for scenario in scenarios]
    metrics = _compute_metrics(rows)

    output = {
        "metadata": {
            "scenario_count": len(scenarios),
            "food_count": len(foods),
            "constraint_count": len(constraints),
            "variants": VARIANTS,
            "note": (
                "Ablations reuse the structured 90-scenario recommendations. "
                "They test verifier module removal, not new recommendation generation."
            ),
        },
        "metrics": metrics,
        "scenarios": rows,
    }

    json_path = _resolve_path(args.output_json)
    md_path = _resolve_path(args.output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(output), encoding="utf-8")

    print(f"Saved ablation JSON to {json_path}")
    print(f"Saved ablation table to {md_path}")
    print()
    for row in metrics["variant_metrics"]:
        print(
            f"{row['variant']}: "
            f"problem_detection_rate={_fmt(row['problem_detection_rate'])}, "
            f"expected_conflict_detection_rate={_fmt(row['expected_conflict_detection_rate'])}, "
            f"evidence_traceability_rate={_fmt(row['evidence_traceability_rate'])}"
        )


def _evaluate_scenario(
    scenario: TestScenario,
    foods: dict,
    constraints: list[NutrientConstraint],
) -> dict:
    active_constraints = select_active_constraints(
        constraints,
        scenario.diseases,
        scenario.risk_factors,
    )
    nutrient_totals = compute_nutrient_totals(scenario.recommended_foods, foods)

    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "diseases": scenario.diseases,
        "risk_factors": scenario.risk_factors,
        "meal_type": scenario.meal_type,
        "expected_passed": scenario.expected_passed,
        "expected_conflict_nutrient": scenario.expected_conflict_nutrient,
        "variants": {
            variant: _evaluate_variant(
                variant,
                nutrient_totals,
                active_constraints,
                scenario.meal_type,
                scenario.expected_conflict_nutrient,
            )
            for variant in VARIANTS
        },
    }


def _evaluate_variant(
    variant: str,
    nutrient_totals: dict[str, float],
    active_constraints: list[NutrientConstraint],
    meal_type: str,
    expected_conflict_nutrient: str,
) -> dict:
    constraints = _constraints_for_variant(variant, active_constraints)

    if variant == "without_nutrient_range":
        verification = _empty_verification(meal_type)
    else:
        verification = verify_nutrient_ranges(nutrient_totals, constraints, meal_type=meal_type)

    if variant == "without_conflict_detection":
        conflicts = _empty_conflicts()
    else:
        conflicts = detect_interval_conflicts(constraints)

    evidence = build_evidence_report(verification, conflicts)
    if variant == "without_evidence_provenance":
        evidence = {
            **evidence,
            "evidence_sources": [],
        }

    detected_problem = (not verification["passed"]) or conflicts["has_conflict"]
    evidence_required = detected_problem
    evidence_traceable = (not evidence_required) or bool(evidence.get("evidence_sources"))

    return {
        "passed": not detected_problem,
        "detected_problem": detected_problem,
        "violation_count": len(verification.get("violations", [])),
        "conflict_count": len(conflicts.get("conflicts", [])),
        "missing_data_count": len(verification.get("missing_data", [])),
        "active_constraint_count": len(constraints),
        "violated_nutrients": sorted({
            violation["nutrient"]
            for violation in verification.get("violations", [])
        }),
        "conflict_nutrients": sorted({
            conflict["nutrient"]
            for conflict in conflicts.get("conflicts", [])
        }),
        "expected_conflict_detected": _conflict_detected_for(conflicts, expected_conflict_nutrient),
        "evidence_source_count": len(evidence.get("evidence_sources", [])),
        "evidence_traceable": evidence_traceable,
    }


def _constraints_for_variant(
    variant: str,
    active_constraints: list[NutrientConstraint],
) -> list[NutrientConstraint]:
    if variant != "rda_only_constraints":
        return active_constraints

    return [
        replace(
            constraint,
            lower_bound=None if constraint.priority != "general-DRI" else constraint.lower_bound,
            upper_bound=None if constraint.priority != "general-DRI" else constraint.upper_bound,
            priority="general-DRI",
            constraint_type="soft",
        )
        for constraint in active_constraints
        if constraint.priority == "general-DRI"
    ]


def _empty_verification(meal_type: str) -> dict:
    return {
        "passed": True,
        "violations": [],
        "missing_data": [],
        "meal_type": meal_type,
        "allocation_factor": None,
    }


def _empty_conflicts() -> dict:
    return {
        "has_conflict": False,
        "conflicts": [],
        "merged_intervals": {},
    }


def _compute_metrics(rows: list[dict]) -> dict:
    scenario_count = len(rows)
    expected_unsafe_rows = [
        row for row in rows
        if row["expected_passed"] is False
    ]
    expected_conflict_rows = [
        row for row in rows
        if row["expected_conflict_nutrient"]
    ]

    variant_metrics = []
    for variant in VARIANTS:
        results = [row["variants"][variant] for row in rows]
        expected_unsafe_detected = sum(
            1
            for row in expected_unsafe_rows
            if row["variants"][variant]["detected_problem"]
        )
        expected_conflicts_detected = sum(
            1
            for row in expected_conflict_rows
            if row["variants"][variant]["expected_conflict_detected"]
        )
        problem_detected_count = sum(1 for result in results if result["detected_problem"])
        passed_count = sum(1 for result in results if result["passed"])
        evidence_required_count = problem_detected_count
        traceable_count = sum(
            1
            for result in results
            if result["detected_problem"] and result["evidence_traceable"]
        )

        variant_metrics.append({
            "variant": variant,
            "label": VARIANT_LABELS[variant],
            "passed_count": passed_count,
            "problem_detected_count": problem_detected_count,
            "problem_detection_rate": _ratio(problem_detected_count, scenario_count),
            "expected_unsafe_detection_rate": _ratio(
                expected_unsafe_detected,
                len(expected_unsafe_rows),
            ),
            "expected_conflicts_detected": expected_conflicts_detected,
            "expected_conflict_count": len(expected_conflict_rows),
            "expected_conflict_detection_rate": _ratio(
                expected_conflicts_detected,
                len(expected_conflict_rows),
            ),
            "total_violation_count": sum(result["violation_count"] for result in results),
            "total_conflict_count": sum(result["conflict_count"] for result in results),
            "evidence_required_count": evidence_required_count,
            "evidence_traceable_count": traceable_count,
            "evidence_traceability_rate": _ratio(traceable_count, evidence_required_count),
        })

    full = next(row for row in variant_metrics if row["variant"] == "full_system")
    deltas = []
    for row in variant_metrics:
        if row["variant"] == "full_system":
            continue
        deltas.append({
            "variant": row["variant"],
            "label": row["label"],
            "lost_problem_detections": (
                full["problem_detected_count"] - row["problem_detected_count"]
            ),
            "lost_expected_conflict_detections": (
                full["expected_conflicts_detected"] - row["expected_conflicts_detected"]
            ),
            "lost_traceable_reports": (
                full["evidence_traceable_count"] - row["evidence_traceable_count"]
            ),
        })

    return {
        "scenario_count": scenario_count,
        "expected_unsafe_count": len(expected_unsafe_rows),
        "expected_conflict_count": len(expected_conflict_rows),
        "variant_metrics": variant_metrics,
        "delta_vs_full": deltas,
        "metric_definitions": {
            "problem_detection_rate": "scenarios flagged by the variant / all scenarios",
            "expected_unsafe_detection_rate": (
                "expected unsafe scenarios flagged by the variant / expected unsafe scenarios"
            ),
            "expected_conflict_detection_rate": (
                "expected conflict scenarios with the expected nutrient conflict detected / expected conflict scenarios"
            ),
            "evidence_traceability_rate": (
                "problem reports with at least one guideline evidence source / problem reports"
            ),
        },
    }


def _render_markdown(output: dict) -> str:
    metrics = output["metrics"]
    lines = [
        "# Ablation Study",
        "",
        "## Important Limitation",
        "",
        (
            "This ablation uses the structured 90-scenario prototype set and "
            "scenario-design labels. It evaluates verifier modules, not an "
            "independently adjudicated clinical benchmark."
        ),
        "",
        "## Variant Metrics",
        "",
        "| Variant | Passed | Problems Detected | Problem Detection Rate | Expected Unsafe Detection Rate | Expected Conflicts Detected | Expected Conflict Detection Rate | Evidence Traceability Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics["variant_metrics"]:
        lines.append(
            "| "
            f"{row['label']} | "
            f"{row['passed_count']} | "
            f"{row['problem_detected_count']} | "
            f"{_fmt(row['problem_detection_rate'])} | "
            f"{_fmt(row['expected_unsafe_detection_rate'])} | "
            f"{row['expected_conflicts_detected']}/{row['expected_conflict_count']} | "
            f"{_fmt(row['expected_conflict_detection_rate'])} | "
            f"{_fmt(row['evidence_traceability_rate'])} |"
        )

    lines.extend([
        "",
        "## Delta vs Full System",
        "",
        "| Variant | Lost Problem Detections | Lost Expected Conflict Detections | Lost Traceable Reports |",
        "|---|---:|---:|---:|",
    ])
    for row in metrics["delta_vs_full"]:
        lines.append(
            "| "
            f"{row['label']} | "
            f"{row['lost_problem_detections']} | "
            f"{row['lost_expected_conflict_detections']} | "
            f"{row['lost_traceable_reports']} |"
        )

    lines.extend([
        "",
        "## Metric Definitions",
        "",
    ])
    for name, definition in metrics["metric_definitions"].items():
        lines.append(f"- `{name}`: {definition}")
    lines.append("")
    return "\n".join(lines)


def _conflict_detected_for(conflict_result: dict, nutrient: str) -> bool:
    if not nutrient:
        return False
    return any(
        conflict.get("nutrient") == nutrient
        for conflict in conflict_result.get("conflicts", [])
    )


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
