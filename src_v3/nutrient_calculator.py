"""Nutrient total calculation for recommended foods."""

from __future__ import annotations

import warnings

from .models import FoodItem, RecommendedFood

_MEAL_FACTORS: dict[str, float] = {
    "breakfast": 0.25,
    "lunch": 0.35,
    "dinner": 0.35,
    "snack": 0.05,
    "full_day": 1.0,
    "day": 1.0,
}


def compute_nutrient_totals(
    recommended_foods: list[RecommendedFood],
    food_db: dict[str, FoodItem],
    unmatched_out: list[str] | None = None,
) -> dict[str, float]:
    """Compute serving-weighted nutrient totals.

    Unmatched food names are appended to ``unmatched_out`` when provided,
    instead of being silently dropped.
    """
    totals: dict[str, float] = {}
    for rec in recommended_foods:
        food = food_db.get(rec.name)
        if food is None:
            if unmatched_out is not None:
                unmatched_out.append(rec.name)
            continue
        for nutrient, amount in food.nutrients.items():
            if amount is None:
                continue
            totals[nutrient] = totals.get(nutrient, 0.0) + amount * rec.servings
    return totals


def meal_allocation_factor(meal_type: str | None) -> float:
    if meal_type is None:
        return 1.0
    normalized = meal_type.lower()
    if normalized not in _MEAL_FACTORS:
        warnings.warn(
            f"Unknown meal_type '{meal_type}'; defaulting to full-day factor 1.0. "
            f"Expected one of: {sorted(_MEAL_FACTORS)}",
            stacklevel=2,
        )
    return _MEAL_FACTORS.get(normalized, 1.0)

