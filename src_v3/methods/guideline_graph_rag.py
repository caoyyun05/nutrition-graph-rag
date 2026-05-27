"""Guideline-constrained Graph-RAG verification adapter."""

from __future__ import annotations

from ..conflict_detector import detect_interval_conflicts
from ..csv_loader import select_active_constraints
from ..evidence_report import build_evidence_report
from ..interval_verifier import verify_nutrient_ranges
from ..models import FoodItem, NutrientConstraint, RecommendedFood
from ..nutrient_calculator import compute_nutrient_totals


def evaluate_recommendation(
    recommended_foods: list[RecommendedFood],
    food_db: dict[str, FoodItem],
    all_constraints: list[NutrientConstraint],
    diseases: list[str],
    risk_factors: list[str],
    meal_type: str | None,
) -> dict:
    active_constraints = select_active_constraints(all_constraints, diseases, risk_factors)
    nutrient_totals = compute_nutrient_totals(recommended_foods, food_db)
    verification = verify_nutrient_ranges(nutrient_totals, active_constraints, meal_type=meal_type)
    conflicts = detect_interval_conflicts(active_constraints)
    evidence = build_evidence_report(verification, conflicts)
    return {
        "nutrient_totals": nutrient_totals,
        "active_constraints": [constraint.constraint_id for constraint in active_constraints],
        "active_constraint_details": [
            {
                "constraint_id": constraint.constraint_id,
                "disease": constraint.disease,
                "nutrient": constraint.nutrient,
                "constraint_type": constraint.constraint_type,
                "priority": constraint.priority,
                "condition": constraint.condition,
                "source": constraint.source,
            }
            for constraint in active_constraints
        ],
        "verification": verification,
        "conflicts": conflicts,
        "evidence": evidence,
    }
