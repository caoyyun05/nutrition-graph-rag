"""Deterministic nutrient-range verification."""

from __future__ import annotations

from .models import NutrientConstraint
from .nutrient_calculator import meal_allocation_factor


def _scaled_bound(value: float | None, factor: float) -> float | None:
    if value is None:
        return None
    return value * factor


def verify_nutrient_ranges(
    nutrient_totals: dict[str, float],
    constraints: list[NutrientConstraint],
    meal_type: str | None = None,
) -> dict:
    factor = meal_allocation_factor(meal_type)
    violations: list[dict] = []
    missing_data: list[dict] = []

    for constraint in constraints:
        value = nutrient_totals.get(constraint.nutrient)
        if value is None:
            missing_data.append({
                "constraint_id": constraint.constraint_id,
                "nutrient": constraint.nutrient,
                "disease": constraint.disease,
                "source": constraint.source,
            })
            continue

        lower = _scaled_bound(constraint.lower_bound, factor)
        upper = _scaled_bound(constraint.upper_bound, factor)

        if lower is not None and value < lower:
            violations.append({
                "constraint_id": constraint.constraint_id,
                "disease": constraint.disease,
                "nutrient": constraint.nutrient,
                "value": value,
                "required_min": lower,
                "unit": constraint.unit,
                "type": "below_minimum",
                "priority": constraint.priority,
                "source": constraint.source,
                "condition": constraint.condition,
            })

        if upper is not None and value > upper:
            violations.append({
                "constraint_id": constraint.constraint_id,
                "disease": constraint.disease,
                "nutrient": constraint.nutrient,
                "value": value,
                "allowed_max": upper,
                "unit": constraint.unit,
                "type": "exceeds_maximum",
                "priority": constraint.priority,
                "source": constraint.source,
                "condition": constraint.condition,
            })

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "missing_data": missing_data,
        "meal_type": meal_type,
        "allocation_factor": factor,
    }

