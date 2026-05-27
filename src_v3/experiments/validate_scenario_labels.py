"""Validate scenario expected labels against the current guideline verifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import DATA_DIR, RESULTS_DIR
from ..csv_loader import load_constraints, load_foods
from ..methods.guideline_graph_rag import evaluate_recommendation
from .metrics import conflict_detected_for, summarize_guideline_result
from .scenarios import TestScenario, load_scenarios


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenarios-csv",
        default=str(DATA_DIR / "test_scenarios.csv"),
        help="Scenario CSV path.",
    )
    parser.add_argument("--foods-csv", default=str(DATA_DIR / "foods_extended.csv"))
    parser.add_argument("--constraints-csv", default=str(DATA_DIR / "nutrient_constraints.csv"))
    parser.add_argument(
        "--output-json",
        default="scenario_label_validation.json",
        help="Structured validation output path.",
    )
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="Exit with an error if labels do not match verifier output.",
    )
    args = parser.parse_args()

    foods = load_foods(Path(args.foods_csv))
    constraints = load_constraints(Path(args.constraints_csv))
    scenarios = load_scenarios(Path(args.scenarios_csv))

    rows = [
        _validate_scenario(scenario, foods, constraints)
        for scenario in scenarios
    ]
    mismatches = [row for row in rows if row["mismatches"]]
    output = {
        "metadata": {
            "scenario_count": len(rows),
            "mismatch_count": len(mismatches),
            "note": (
                "Validation compares explicit expected labels in the scenario CSV "
                "against the current guideline verifier output."
            ),
        },
        "mismatches": mismatches,
        "scenarios": rows,
    }

    output_path = _resolve_output_path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Validated {len(rows)} scenarios")
    print(f"Mismatches: {len(mismatches)}")
    print(f"Saved scenario label validation to {output_path}")
    if args.fail_on_mismatch and mismatches:
        raise SystemExit(1)


def _validate_scenario(scenario: TestScenario, foods: dict, constraints: list) -> dict:
    result = evaluate_recommendation(
        recommended_foods=scenario.recommended_foods,
        food_db=foods,
        all_constraints=constraints,
        diseases=scenario.diseases,
        risk_factors=scenario.risk_factors,
        meal_type=scenario.meal_type,
    )
    summary = summarize_guideline_result(result)
    actual_violation_nutrients = sorted({
        violation["nutrient"]
        for violation in result["verification"].get("violations", [])
    })
    actual_missing_data = bool(result["verification"].get("missing_data", []))
    actual_conflict_detected = conflict_detected_for(
        result,
        scenario.expected_conflict_nutrient,
    )

    mismatches = []
    if scenario.expected_passed is not None and scenario.expected_passed != summary["passed"]:
        mismatches.append({
            "field": "expected_passed",
            "expected": scenario.expected_passed,
            "actual": summary["passed"],
        })

    if scenario.expected_violation_nutrients:
        expected_nutrients = sorted(set(scenario.expected_violation_nutrients))
        if expected_nutrients != actual_violation_nutrients:
            mismatches.append({
                "field": "expected_violation_nutrients",
                "expected": expected_nutrients,
                "actual": actual_violation_nutrients,
            })

    if scenario.expected_conflict_nutrient and not actual_conflict_detected:
        mismatches.append({
            "field": "expected_conflict_nutrient",
            "expected": scenario.expected_conflict_nutrient,
            "actual": None,
        })

    if scenario.expected_missing_data is not None and scenario.expected_missing_data != actual_missing_data:
        mismatches.append({
            "field": "expected_missing_data",
            "expected": scenario.expected_missing_data,
            "actual": actual_missing_data,
        })

    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "expected": {
            "passed": scenario.expected_passed,
            "violation_nutrients": scenario.expected_violation_nutrients,
            "conflict_nutrient": scenario.expected_conflict_nutrient,
            "missing_data": scenario.expected_missing_data,
            "label_source": scenario.label_source,
        },
        "actual": {
            "passed": summary["passed"],
            "violation_nutrients": actual_violation_nutrients,
            "conflict_count": summary["conflict_count"],
            "missing_data": actual_missing_data,
        },
        "mismatches": mismatches,
    }


def _resolve_output_path(value: str) -> Path:
    requested_path = Path(value)
    return requested_path if requested_path.is_absolute() else RESULTS_DIR / requested_path


if __name__ == "__main__":
    main()
