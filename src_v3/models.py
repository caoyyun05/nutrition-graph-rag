"""Shared dataclasses for v2 verification logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NutrientConstraint:
    constraint_id: str
    disease: str
    nutrient: str
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    unit: str
    condition: str
    constraint_type: str
    priority: str
    guideline_id: str
    source: str = ""
    note: str = ""


@dataclass(frozen=True)
class FoodItem:
    food_id: str
    name: str
    category: str
    serving_size_g: float
    nutrients: dict[str, Optional[float]]


@dataclass(frozen=True)
class RecommendedFood:
    name: str
    servings: float = 1.0

