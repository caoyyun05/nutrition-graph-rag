"""Boolean Graph-RAG baseline.

This adapter represents food-level suitable/contraindicated filtering. It does
not compute meal nutrient totals or detect interval conflicts.
"""

from __future__ import annotations

from ..models import FoodItem, RecommendedFood


def evaluate_recommendation(
    recommended_foods: list[RecommendedFood],
    food_db: dict[str, FoodItem],
    diseases: list[str] | None = None,
    risk_factors: list[str] | None = None,
) -> dict:
    diseases = diseases or []
    risk_factors = risk_factors or []
    flagged = []
    for rec in recommended_foods:
        food = food_db.get(rec.name)
        if food is None:
            continue
        for reason in _food_level_reasons(food, diseases, risk_factors):
            flagged.append({
                "food": rec.name,
                "category": food.category,
                "reason": reason,
            })
    return {
        "passed": len(flagged) == 0,
        "flagged_foods": flagged,
        "deterministic_verification": False,
        "limitations": [
            "food_level_rules_only",
            "no_serving_weighted_total_check",
            "no_interval_intersection_conflict_check",
        ],
    }


def _food_level_reasons(
    food: FoodItem,
    diseases: list[str],
    risk_factors: list[str],
) -> list[str]:
    reasons: list[str] = []
    nutrients = food.nutrients
    disease_set = set(diseases)
    risk_set = set(risk_factors)

    if "HTN" in disease_set:
        if food.category == "processed" or _gte(nutrients.get("sodium_mg"), 300):
            reasons.append("htn_high_sodium_food")

    if "T2DM" in disease_set:
        if food.category == "beverage" and _gte(nutrients.get("added_sugar_g"), 10):
            reasons.append("t2dm_sugary_beverage")
        if _gte(nutrients.get("added_sugar_g"), 15):
            reasons.append("t2dm_high_added_sugar_food")
        if _gte(nutrients.get("gi"), 70):
            reasons.append("t2dm_high_gi_food")

    if "CKD" in disease_set:
        if "hyperkalemia_risk" in risk_set and _gte(nutrients.get("potassium_mg"), 400):
            reasons.append("ckd_high_potassium_food")
        if (
            {"hyperphosphatemia_risk", "elevated_serum_phosphorus"} & risk_set
            and _gte(nutrients.get("phosphorus_mg"), 220)
        ):
            reasons.append("ckd_high_phosphorus_food")
        if _gte(nutrients.get("sodium_mg"), 500):
            reasons.append("ckd_high_sodium_food")

    return reasons


def _gte(value: float | None, threshold: float) -> bool:
    return value is not None and value >= threshold
