"""Guideline-Prompted LLM verifier baseline.

This baseline injects the same KG-derived nutrient constraints into the LLM
prompt and asks the model to judge whether a recommendation violates any
constraint. It tests whether an LLM can perform the verification task when
given explicit numeric bounds, without deterministic computation.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..csv_loader import select_active_constraints
from ..models import FoodItem, NutrientConstraint, RecommendedFood
from ..nutrient_calculator import meal_allocation_factor


def build_verification_prompt(
    recommended_foods: list[RecommendedFood],
    food_db: dict[str, FoodItem],
    active_constraints: list[NutrientConstraint],
    meal_type: str | None,
) -> str:
    factor = meal_allocation_factor(meal_type)
    factor_note = ""
    if meal_type and meal_type.lower() != "full_day":
        factor_note = (
            f"\nNote: This is a {meal_type} meal. "
            f"Apply allocation factor {factor} to daily bounds "
            f"(multiply each bound by {factor})."
        )

    constraint_lines = []
    for c in active_constraints:
        parts = [f"  - {c.nutrient} ({c.disease})"]
        if c.lower_bound is not None:
            parts.append(f"lower >= {c.lower_bound * factor:.1f} {c.unit}")
        if c.upper_bound is not None:
            parts.append(f"upper <= {c.upper_bound * factor:.1f} {c.unit}")
        if c.condition:
            parts.append(f"[condition: {c.condition}]")
        constraint_lines.append(", ".join(parts))

    food_lines = []
    for rec in recommended_foods:
        food = food_db.get(rec.name)
        if food is None:
            food_lines.append(f"  - {rec.name}: {rec.servings} serving(s) [NOT IN DATABASE]")
            continue
        nutrients_str = ", ".join(
            f"{k}={v}" for k, v in food.nutrients.items() if v is not None
        )
        food_lines.append(
            f"  - {rec.name}: {rec.servings} serving(s) "
            f"[per serving: {nutrients_str}]"
        )

    return (
        "You are a clinical nutrition safety verifier. Given the nutrient constraints "
        "and food recommendations below, determine whether any constraint is violated.\n\n"
        "## Active Nutrient Constraints\n"
        + "\n".join(constraint_lines)
        + factor_note
        + "\n\n## Recommended Foods (with per-serving nutrient values)\n"
        + "\n".join(food_lines)
        + "\n\n## Task\n"
        "1. Calculate the total nutrients from the recommended foods.\n"
        "2. Check each constraint against the totals.\n"
        "3. Check if any two constraints on the same nutrient create an infeasible "
        "interval (lower > upper).\n\n"
        "Return ONLY a JSON object with this structure:\n"
        '{"passed": true/false, "violated_nutrients": ["nutrient1", ...], '
        '"conflict_nutrients": ["nutrient1", ...], '
        '"reasoning": "brief explanation"}'
    )


def parse_llm_judgment(raw_output: str) -> dict:
    """Parse the LLM's JSON judgment into a structured result."""
    try:
        payload = _extract_json(raw_output)
        if payload is None:
            return _fallback_result(raw_output)
        return {
            "passed": bool(payload.get("passed", True)),
            "violated_nutrients": payload.get("violated_nutrients", []),
            "conflict_nutrients": payload.get("conflict_nutrients", []),
            "reasoning": payload.get("reasoning", ""),
            "parse_success": True,
        }
    except (TypeError, ValueError, KeyError):
        return _fallback_result(raw_output)


def evaluate_recommendation(
    recommended_foods: list[RecommendedFood],
    food_db: dict[str, FoodItem],
    all_constraints: list[NutrientConstraint],
    diseases: list[str],
    risk_factors: list[str],
    meal_type: str | None,
    llm_output: str | None = None,
) -> dict:
    """Evaluate using LLM judgment with constraints injected into prompt.

    If ``llm_output`` is provided (saved replay), it is parsed directly.
    Otherwise the caller must supply the raw LLM response externally.
    """
    active_constraints = select_active_constraints(all_constraints, diseases, risk_factors)
    prompt = build_verification_prompt(
        recommended_foods, food_db, active_constraints, meal_type,
    )

    if llm_output is None:
        return {
            "passed": None,
            "prompt": prompt,
            "deterministic_verification": False,
            "detected_problem": False,
            "judgment": None,
            "limitations": ["no_llm_output_provided"],
        }

    judgment = parse_llm_judgment(llm_output)
    detected_problem = not judgment["passed"]

    return {
        "passed": judgment["passed"],
        "prompt": prompt,
        "deterministic_verification": False,
        "detected_problem": detected_problem,
        "judgment": judgment,
        "violated_nutrients": judgment.get("violated_nutrients", []),
        "conflict_nutrients": judgment.get("conflict_nutrients", []),
        "limitations": [
            "llm_numerical_reasoning_may_be_inaccurate",
            "non_deterministic_output",
        ],
    }


def _extract_json(text: str) -> Any | None:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass
    obj_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _fallback_result(raw_output: str) -> dict:
    lower = raw_output.lower()
    passed = "pass" in lower and "fail" not in lower and "violat" not in lower
    return {
        "passed": passed,
        "violated_nutrients": [],
        "conflict_nutrients": [],
        "reasoning": "parse_failed_fallback",
        "parse_success": False,
    }
