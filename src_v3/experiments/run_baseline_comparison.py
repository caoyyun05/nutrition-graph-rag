"""Run first-pass baseline comparison on local v2 scenarios.

The current baselines are deterministic placeholders. They are useful for
debugging the experimental contract before real LLM output extraction is wired.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import DATA_DIR, RESULTS_DIR
from ..csv_loader import load_constraints, load_foods
from ..methods import boolean_graph_rag, guideline_graph_rag, pure_kg, pure_llm
from .metrics import conflict_detected_for, summarize_guideline_result
from .scenarios import TestScenario, load_scenarios


METHODS = [
    "pure_llm",
    "pure_kg",
    "boolean_graph_rag",
    "guideline_graph_rag",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-json",
        default="baseline_comparison.json",
        help="Path for saving structured comparison results.",
    )
    parser.add_argument("--foods-csv", default=str(DATA_DIR / "foods_extended.csv"))
    parser.add_argument("--constraints-csv", default=str(DATA_DIR / "nutrient_constraints.csv"))
    parser.add_argument("--scenarios-csv", default=str(DATA_DIR / "test_scenarios.csv"))
    args = parser.parse_args()

    foods = load_foods(Path(args.foods_csv))
    constraints = load_constraints(Path(args.constraints_csv))
    scenarios = load_scenarios(Path(args.scenarios_csv))

    rows = []
    for scenario in scenarios:
        rows.append(_evaluate_scenario(scenario, foods, constraints))

    aggregate = _aggregate(rows)
    output = {
        "metadata": {
            "food_count": len(foods),
            "constraint_count": len(constraints),
            "scenario_count": len(scenarios),
            "methods": METHODS,
            "note": "First-pass comparison with placeholder baselines.",
        },
        "aggregate": aggregate,
        "scenarios": rows,
    }

    output_path = _resolve_output_path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    _print_summary(output_path, aggregate)


def _evaluate_scenario(scenario: TestScenario, foods: dict, constraints: list) -> dict:
    pure_llm_result = pure_llm.evaluate_recommendation(scenario.recommended_foods)
    pure_kg_result = pure_kg.evaluate_recommendation(scenario.recommended_foods, foods)
    boolean_result = boolean_graph_rag.evaluate_recommendation(
        scenario.recommended_foods,
        foods,
        diseases=scenario.diseases,
        risk_factors=scenario.risk_factors,
    )
    guideline_result = guideline_graph_rag.evaluate_recommendation(
        recommended_foods=scenario.recommended_foods,
        food_db=foods,
        all_constraints=constraints,
        diseases=scenario.diseases,
        risk_factors=scenario.risk_factors,
        meal_type=scenario.meal_type,
    )
    guideline_summary = summarize_guideline_result(guideline_result)

    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "diseases": scenario.diseases,
        "risk_factors": scenario.risk_factors,
        "meal_type": scenario.meal_type,
        "recommended_foods": [
            {"name": food.name, "servings": food.servings}
            for food in scenario.recommended_foods
        ],
        "expected_conflict_nutrient": scenario.expected_conflict_nutrient,
        "expected_conflict_detected": conflict_detected_for(
            guideline_result,
            scenario.expected_conflict_nutrient,
        ),
        "methods": {
            "pure_llm": _summarize_pure_llm(pure_llm_result),
            "pure_kg": _summarize_pure_kg(pure_kg_result),
            "boolean_graph_rag": _summarize_boolean(boolean_result),
            "guideline_graph_rag": {
                "passed": guideline_summary["passed"],
                "deterministic_verification": True,
                "detected_problem": not guideline_summary["passed"],
                "violation_count": guideline_summary["violation_count"],
                "conflict_count": guideline_summary["conflict_count"],
                "missing_data_count": guideline_summary["missing_data_count"],
                "active_constraint_count": guideline_summary["active_constraint_count"],
                "violated_nutrients": sorted({
                    violation["nutrient"]
                    for violation in guideline_result["verification"].get("violations", [])
                }),
                "conflict_nutrients": sorted({
                    conflict["nutrient"]
                    for conflict in guideline_result["conflicts"].get("conflicts", [])
                }),
                "evidence_sources": guideline_result["evidence"].get("evidence_sources", []),
            },
        },
    }


def _summarize_pure_llm(result: dict) -> dict:
    return {
        "passed": result["passed"],
        "deterministic_verification": result["deterministic_verification"],
        "detected_problem": result["detected_problem"],
        "food_count": result["food_count"],
        "limitations": result["limitations"],
    }


def _summarize_pure_kg(result: dict) -> dict:
    return {
        "passed": result["passed"],
        "deterministic_verification": False,
        "detected_problem": not result["passed"],
        "missing_food_count": len(result["missing_foods"]),
        "missing_nutrient_record_count": len(result["missing_nutrients"]),
        "missing_foods": result["missing_foods"],
        "missing_nutrients": result["missing_nutrients"],
        "limitations": result["limitations"],
    }


def _summarize_boolean(result: dict) -> dict:
    return {
        "passed": result["passed"],
        "deterministic_verification": False,
        "detected_problem": not result["passed"],
        "flagged_food_count": len(result["flagged_foods"]),
        "flagged_foods": result["flagged_foods"],
        "limitations": result["limitations"],
    }


def _aggregate(rows: list[dict]) -> dict:
    totals = {
        method: {
            "passed_count": 0,
            "failed_count": 0,
            "unknown_count": 0,
            "problem_detected_count": 0,
        }
        for method in METHODS
    }

    guideline_failures = 0
    guideline_conflict_scenarios = 0
    expected_conflict_scenarios = 0
    expected_conflicts_detected = 0

    for row in rows:
        guideline = row["methods"]["guideline_graph_rag"]
        if not guideline["passed"]:
            guideline_failures += 1
        if guideline["conflict_count"] > 0:
            guideline_conflict_scenarios += 1
        if row["expected_conflict_nutrient"]:
            expected_conflict_scenarios += 1
            if row["expected_conflict_detected"]:
                expected_conflicts_detected += 1

        for method, result in row["methods"].items():
            if result["passed"] is True:
                totals[method]["passed_count"] += 1
            elif result["passed"] is False:
                totals[method]["failed_count"] += 1
            else:
                totals[method]["unknown_count"] += 1
            if result.get("detected_problem"):
                totals[method]["problem_detected_count"] += 1

    scenario_count = len(rows)
    for method, stats in totals.items():
        stats["pass_rate"] = _ratio(stats["passed_count"], scenario_count)
        stats["problem_detection_rate"] = _ratio(stats["problem_detected_count"], scenario_count)

    return {
        "scenario_count": scenario_count,
        "method_totals": totals,
        "guideline_failure_count": guideline_failures,
        "guideline_failure_rate": _ratio(guideline_failures, scenario_count),
        "guideline_conflict_scenarios": guideline_conflict_scenarios,
        "expected_conflict_scenarios": expected_conflict_scenarios,
        "expected_conflicts_detected": expected_conflicts_detected,
        "expected_conflict_detection_rate": _ratio(
            expected_conflicts_detected,
            expected_conflict_scenarios,
        ),
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _resolve_output_path(value: str) -> Path:
    requested_path = Path(value)
    return requested_path if requested_path.is_absolute() else RESULTS_DIR / requested_path


def _print_summary(output_path: Path, aggregate: dict) -> None:
    print(f"Saved baseline comparison to {output_path}")
    print()
    print(f"Scenarios: {aggregate['scenario_count']}")
    print(
        "Guideline-constrained failures: "
        f"{aggregate['guideline_failure_count']} "
        f"({aggregate['guideline_failure_rate']})"
    )
    print(
        "Expected conflict detection: "
        f"{aggregate['expected_conflicts_detected']}/"
        f"{aggregate['expected_conflict_scenarios']} "
        f"({aggregate['expected_conflict_detection_rate']})"
    )
    print()
    for method, stats in aggregate["method_totals"].items():
        print(
            f"{method}: "
            f"passed={stats['passed_count']} "
            f"failed={stats['failed_count']} "
            f"unknown={stats['unknown_count']} "
            f"problem_detected={stats['problem_detected_count']}"
        )


if __name__ == "__main__":
    main()
