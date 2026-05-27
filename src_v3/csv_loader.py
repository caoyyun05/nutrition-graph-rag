"""Local CSV loaders for v2 experiments.

These loaders keep the first experimental loop independent from Neo4j. The
same CSV files can later be imported into the graph database.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .models import FoodItem, NutrientConstraint, RecommendedFood


NUTRIENT_COLUMNS = [
    "energy_kcal",
    "protein_g",
    "carbohydrate_g",
    "fat_g",
    "fiber_g",
    "sodium_mg",
    "potassium_mg",
    "phosphorus_mg",
    "added_sugar_g",
    "gi",
]


def load_foods(path: Path) -> dict[str, FoodItem]:
    foods: dict[str, FoodItem] = {}
    for row in _read_csv(path):
        nutrients = {column: _optional_float(row.get(column)) for column in NUTRIENT_COLUMNS}
        food = FoodItem(
            food_id=row["food_id"],
            name=row["name"],
            category=row["category"],
            serving_size_g=float(row["serving_size_g"]),
            nutrients=nutrients,
        )
        foods[food.name] = food
    return foods


def load_constraints(path: Path) -> list[NutrientConstraint]:
    constraints: list[NutrientConstraint] = []
    for row in _read_csv(path):
        constraints.append(
            NutrientConstraint(
                constraint_id=row["constraint_id"],
                disease=row["disease"],
                nutrient=row["nutrient"],
                lower_bound=_optional_float(row.get("lower_bound")),
                upper_bound=_optional_float(row.get("upper_bound")),
                unit=row["unit"],
                condition=row.get("condition", ""),
                constraint_type=row["constraint_type"],
                priority=row["priority"],
                guideline_id=row["guideline_id"],
                source=row.get("source", ""),
                note=row.get("note", ""),
            )
        )
    return constraints


def parse_recommended_foods(value: str) -> list[RecommendedFood]:
    foods: list[RecommendedFood] = []
    if not value:
        return foods
    for item in value.split(";"):
        if not item.strip():
            continue
        name, _, servings = item.partition(":")
        foods.append(RecommendedFood(name=name.strip(), servings=float(servings or 1)))
    return foods


def select_active_constraints(
    constraints: Iterable[NutrientConstraint],
    diseases: Iterable[str],
    risk_factors: Iterable[str] | None = None,
) -> list[NutrientConstraint]:
    disease_set = {d.strip() for d in diseases if d.strip()}
    risk_set = {r.strip().lower() for r in (risk_factors or []) if r.strip()}
    return [
        constraint
        for constraint in constraints
        if constraint.disease in disease_set and _condition_is_active(constraint.condition, risk_set)
    ]


def _condition_is_active(condition: str, risk_factors: set[str]) -> bool:
    normalized = condition.lower()
    if not normalized:
        return True
    if "hyperkalemia" in normalized:
        return bool({"hyperkalemia_risk", "advanced_ckd", "dialysis"} & risk_factors)
    if "hyperphosphatemia" in normalized:
        return bool({"hyperphosphatemia_risk", "advanced_ckd", "dialysis"} & risk_factors)
    if "elevated_serum_phosphorus" in normalized or "elevated serum phosphorus" in normalized:
        return "elevated_serum_phosphorus" in risk_factors
    return True


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
