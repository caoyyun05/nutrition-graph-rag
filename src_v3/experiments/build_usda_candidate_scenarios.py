"""Build USDA-candidate scenarios without modifying the v2 scenario file."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ..config import DATA_DIR, ROOT_DIR
from ..csv_loader import load_constraints, load_foods
from ..methods.guideline_graph_rag import evaluate_recommendation
from ..models import RecommendedFood
from .metrics import conflict_detected_for, summarize_guideline_result
from .scenarios import load_scenarios


USDA_DATA_DIR = ROOT_DIR / "data_usda_55"

FIELDNAMES = [
    "scenario_id",
    "name",
    "diseases",
    "risk_factors",
    "meal_type",
    "recommended_foods",
    "expected_passed",
    "expected_violation_nutrients",
    "expected_conflict_nutrient",
    "expected_missing_data",
    "label_source",
    "notes",
]

FOOD_NAME_MAP = {
    "Low-sodium yogurt": "Low-fat yogurt",
    "Instant noodles": "Ramen noodles",
    "Sugary cereal": "Sweetened cereal",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-scenarios-csv", default=str(DATA_DIR / "test_scenarios.csv"))
    parser.add_argument("--foods-csv", default=str(USDA_DATA_DIR / "foods_usda_55.csv"))
    parser.add_argument("--constraints-csv", default=str(DATA_DIR / "nutrient_constraints.csv"))
    parser.add_argument("--output-csv", default=str(USDA_DATA_DIR / "test_scenarios_usda_90.csv"))
    args = parser.parse_args()

    foods = load_foods(Path(args.foods_csv))
    constraints = load_constraints(Path(args.constraints_csv))
    source_scenarios = load_scenarios(Path(args.source_scenarios_csv))

    rows = []
    for scenario in source_scenarios:
        mapped_foods = [
            {
                "name": FOOD_NAME_MAP.get(food.name, food.name),
                "servings": food.servings,
            }
            for food in scenario.recommended_foods
        ]
        result = evaluate_recommendation(
            recommended_foods=[
                RecommendedFood(name=food["name"], servings=food["servings"])
                for food in mapped_foods
            ],
            food_db=foods,
            all_constraints=constraints,
            diseases=scenario.diseases,
            risk_factors=scenario.risk_factors,
            meal_type=scenario.meal_type,
        )
        summary = summarize_guideline_result(result)
        violation_nutrients = sorted({
            violation["nutrient"]
            for violation in result["verification"].get("violations", [])
        })
        conflict_nutrient = (
            scenario.expected_conflict_nutrient
            if conflict_detected_for(result, scenario.expected_conflict_nutrient)
            else ""
        )
        missing_data = bool(result["verification"].get("missing_data", []))
        rows.append({
            "scenario_id": scenario.scenario_id,
            "name": f"{scenario.name} [USDA candidate]",
            "diseases": "|".join(scenario.diseases),
            "risk_factors": "|".join(scenario.risk_factors),
            "meal_type": scenario.meal_type,
            "recommended_foods": ";".join(
                f"{food['name']}:{_fmt_servings(food['servings'])}"
                for food in mapped_foods
            ),
            "expected_passed": str(summary["passed"]).lower(),
            "expected_violation_nutrients": "|".join(violation_nutrients),
            "expected_conflict_nutrient": conflict_nutrient,
            "expected_missing_data": str(missing_data).lower(),
            "label_source": "usda_candidate_verifier_recomputed_2026-05-26",
            "notes": (
                f"Recomputed from {scenario.scenario_id} using data_usda_55 foods; "
                f"original note: {scenario.notes}"
            ),
        })

    output_path = Path(args.output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} USDA candidate scenarios to {output_path}")


def _fmt_servings(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)


if __name__ == "__main__":
    main()
