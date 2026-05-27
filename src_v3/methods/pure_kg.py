"""Simple KG-only baseline.

The KG-only baseline checks whether foods exist in the structured database and
whether their key nutrient fields are available. It does not apply executable
nutrient intervals, meal allocation, or comorbidity conflict detection.
"""

from __future__ import annotations

from ..models import FoodItem, RecommendedFood


KEY_NUTRIENTS = [
    "sodium_mg",
    "potassium_mg",
    "phosphorus_mg",
    "fiber_g",
    "carbohydrate_g",
    "added_sugar_g",
]


def evaluate_recommendation(
    recommended_foods: list[RecommendedFood],
    food_db: dict[str, FoodItem],
) -> dict:
    missing = [food.name for food in recommended_foods if food.name not in food_db]
    missing_nutrients = []
    for rec in recommended_foods:
        food = food_db.get(rec.name)
        if food is None:
            continue
        absent = [
            nutrient
            for nutrient in KEY_NUTRIENTS
            if food.nutrients.get(nutrient) is None
        ]
        if absent:
            missing_nutrients.append({"food": rec.name, "missing_nutrients": absent})

    passed = not missing and not missing_nutrients
    return {
        "passed": passed,
        "missing_foods": missing,
        "missing_nutrients": missing_nutrients,
        "deterministic_verification": False,
        "limitations": [
            "no_nutrient_interval_check",
            "no_meal_allocation",
            "no_comorbidity_conflict_check",
        ],
    }
