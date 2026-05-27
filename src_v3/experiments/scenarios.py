"""Scenario loading for local v2 experiments."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ..csv_loader import parse_recommended_foods
from ..models import RecommendedFood


@dataclass(frozen=True)
class TestScenario:
    scenario_id: str
    name: str
    diseases: list[str]
    risk_factors: list[str]
    meal_type: str
    recommended_foods: list[RecommendedFood]
    expected_passed: bool | None
    expected_violation_nutrients: list[str]
    expected_conflict_nutrient: str
    expected_missing_data: bool | None
    label_source: str
    notes: str


def load_scenarios(path: Path) -> list[TestScenario]:
    scenarios: list[TestScenario] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            scenarios.append(
                TestScenario(
                    scenario_id=row["scenario_id"],
                    name=row["name"],
                    diseases=_split_pipe(row.get("diseases", "")),
                    risk_factors=_split_pipe(row.get("risk_factors", "")),
                    meal_type=row.get("meal_type", "full_day"),
                    recommended_foods=parse_recommended_foods(row.get("recommended_foods", "")),
                    expected_passed=_optional_bool(row.get("expected_passed", "")),
                    expected_violation_nutrients=_split_pipe(row.get("expected_violation_nutrients", "")),
                    expected_conflict_nutrient=row.get("expected_conflict_nutrient", ""),
                    expected_missing_data=_optional_bool(row.get("expected_missing_data", "")),
                    label_source=row.get("label_source", ""),
                    notes=row.get("notes", ""),
                )
            )
    return scenarios


def _split_pipe(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def _optional_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean label: {value}")
