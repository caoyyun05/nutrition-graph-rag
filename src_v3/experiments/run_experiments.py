"""Run the first local v2 smoke experiments.

This script verifies that the executable-constraint chain works before the
project depends on Neo4j or an LLM API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import DATA_DIR, RESULTS_DIR
from ..csv_loader import load_constraints, load_foods
from ..methods.guideline_graph_rag import evaluate_recommendation
from .metrics import conflict_detected_for, summarize_guideline_result
from .scenarios import load_scenarios


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional path for saving structured experiment results.",
    )
    parser.add_argument("--foods-csv", default=str(DATA_DIR / "foods_extended.csv"))
    parser.add_argument("--constraints-csv", default=str(DATA_DIR / "nutrient_constraints.csv"))
    parser.add_argument("--scenarios-csv", default=str(DATA_DIR / "test_scenarios.csv"))
    args = parser.parse_args()

    foods = load_foods(Path(args.foods_csv))
    constraints = load_constraints(Path(args.constraints_csv))
    scenarios = load_scenarios(Path(args.scenarios_csv))
    structured_results = []

    print(f"Loaded {len(foods)} foods, {len(constraints)} constraints, {len(scenarios)} scenarios")
    print()

    for scenario in scenarios:
        result = evaluate_recommendation(
            recommended_foods=scenario.recommended_foods,
            food_db=foods,
            all_constraints=constraints,
            diseases=scenario.diseases,
            risk_factors=scenario.risk_factors,
            meal_type=scenario.meal_type,
        )
        summary = summarize_guideline_result(result)
        expected_conflict_hit = conflict_detected_for(result, scenario.expected_conflict_nutrient)
        structured_results.append(
            {
                "scenario_id": scenario.scenario_id,
                "name": scenario.name,
                "diseases": scenario.diseases,
                "risk_factors": scenario.risk_factors,
                "meal_type": scenario.meal_type,
                "recommended_foods": [
                    {"name": food.name, "servings": food.servings}
                    for food in scenario.recommended_foods
                ],
                "summary": summary,
                "expected_conflict_nutrient": scenario.expected_conflict_nutrient,
                "expected_conflict_detected": expected_conflict_hit,
                "result": result,
            }
        )

        print(f"{scenario.scenario_id} | {scenario.name}")
        print(f"  diseases={','.join(scenario.diseases)} risk_factors={','.join(scenario.risk_factors) or 'none'}")
        print(
            "  "
            f"passed={summary['passed']} "
            f"violations={summary['violation_count']} "
            f"conflicts={summary['conflict_count']} "
            f"missing_data={summary['missing_data_count']} "
            f"active_constraints={summary['active_constraint_count']}"
        )
        if scenario.expected_conflict_nutrient:
            print(f"  expected_conflict={scenario.expected_conflict_nutrient} detected={expected_conflict_hit}")
        if result["verification"]["violations"]:
            for violation in result["verification"]["violations"]:
                print(
                    "  violation: "
                    f"{violation['disease']} {violation['nutrient']} "
                    f"value={violation['value']:.1f} {violation['unit']}"
                )
        if result["conflicts"]["conflicts"]:
            for conflict in result["conflicts"]["conflicts"]:
                print(
                    "  conflict: "
                    f"{conflict['nutrient']} "
                    f"merged_lower={conflict['merged_lower']} "
                    f"merged_upper={conflict['merged_upper']} "
                    f"resolution={conflict['resolution']['selected_constraint_id']}"
                )
        print()

    if args.output_json:
        requested_path = Path(args.output_json)
        output_path = requested_path if requested_path.is_absolute() else RESULTS_DIR / requested_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(structured_results, file, ensure_ascii=False, indent=2)
        print(f"Saved structured results to {output_path}")


if __name__ == "__main__":
    main()
