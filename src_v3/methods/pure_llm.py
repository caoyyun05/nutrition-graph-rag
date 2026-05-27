"""Pure LLM baseline marker.

The actual pure-LLM baseline should call a configured model and store raw
outputs. This local baseline models an unverified LLM response that returns a
recommendation without deterministic food, nutrient, or guideline checks.
"""

from __future__ import annotations

from ..llm_food_extractor import extract_recommended_foods
from ..models import FoodItem, RecommendedFood


def evaluate_recommendation(
    recommended_foods: list[RecommendedFood],
    raw_output: str | None = None,
    food_db: dict[str, FoodItem] | None = None,
) -> dict:
    extraction = None
    if raw_output is not None and food_db is not None:
        extraction = extract_recommended_foods(raw_output, food_db)
        recommended_foods = extraction["recommended_foods"]

    return {
        "passed": True,
        "food_count": len(recommended_foods),
        "deterministic_verification": False,
        "detected_problem": False,
        "extraction": extraction,
        "limitations": [
            "no_nutrient_interval_check",
            "no_comorbidity_conflict_check",
            "no_evidence_traceability",
        ],
    }
