"""Extract recommended foods from LLM text outputs.

The extractor is intentionally deterministic. It first tries structured JSON and
then falls back to food-name matching against the local food database.
"""

from __future__ import annotations

import functools
import json
import re
from typing import Any

from .models import FoodItem, RecommendedFood


_SERVING_PATTERN_TEMPLATES = [
    r"(?P<food>{food})\s*[:：]\s*(?P<servings>\d+(?:\.\d+)?)",
    r"(?P<servings>\d+(?:\.\d+)?)\s*(?:serving|servings|份|份量|portion|portions)\s+(?:of\s+)?(?P<food>{food})",
    r"(?P<food>{food})\s*\((?P<servings>\d+(?:\.\d+)?)\s*(?:serving|servings|份|portion|portions)\)",
]


@functools.lru_cache(maxsize=512)
def _compiled_serving_patterns(food_name: str) -> list[re.Pattern]:
    escaped = re.escape(food_name)
    return [
        re.compile(tmpl.format(food=escaped), re.IGNORECASE)
        for tmpl in _SERVING_PATTERN_TEMPLATES
    ]


def extract_recommended_foods(
    text: str,
    food_db: dict[str, FoodItem],
    default_servings: float = 1.0,
) -> dict:
    """Extract local-food recommendations from free-form or JSON LLM output."""
    json_result = _extract_from_json(text, food_db)
    if json_result["recommended_foods"]:
        return {
            "recommended_foods": json_result["recommended_foods"],
            "unmatched_items": json_result["unmatched_items"],
            "extraction_method": "json",
        }

    text_result = _extract_from_text(text, food_db, default_servings)
    return {
        "recommended_foods": text_result["recommended_foods"],
        "unmatched_items": text_result["unmatched_items"],
        "extraction_method": "text_match",
    }


def _extract_from_json(text: str, food_db: dict[str, FoodItem]) -> dict:
    payload = _load_json_payload(text)
    if payload is None:
        return {"recommended_foods": [], "unmatched_items": []}

    items = _find_food_items(payload)
    foods: list[RecommendedFood] = []
    unmatched: list[str] = []
    for item in items:
        name = str(item.get("name") or item.get("food") or item.get("food_name") or "").strip()
        if not name:
            continue
        matched_name = _match_food_name(name, food_db)
        if matched_name is None:
            unmatched.append(name)
            continue
        foods.append(
            RecommendedFood(
                name=matched_name,
                servings=_safe_float(item.get("servings") or item.get("portion") or item.get("quantity"), 1.0),
            )
        )
    return {"recommended_foods": _dedupe_foods(foods), "unmatched_items": unmatched}


def _extract_from_text(
    text: str,
    food_db: dict[str, FoodItem],
    default_servings: float,
) -> dict:
    foods: list[RecommendedFood] = []
    unmatched: list[str] = []
    compact_text = text.replace("\n", " ")
    for name in sorted(food_db, key=len, reverse=True):
        matched = _find_text_food_match(compact_text, name)
        if matched is None:
            continue
        foods.append(RecommendedFood(name=name, servings=matched))
    return {"recommended_foods": _dedupe_foods(foods, default_servings), "unmatched_items": unmatched}



def _load_json_payload(text: str) -> Any | None:
    stripped = text.strip()
    candidates = [stripped]
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        candidates.insert(0, fenced.group(1).strip())
    object_match = re.search(r"(\{.*\})", stripped, flags=re.DOTALL)
    if object_match:
        candidates.append(object_match.group(1))
    array_match = re.search(r"(\[.*\])", stripped, flags=re.DOTALL)
    if array_match:
        candidates.append(array_match.group(1))

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _find_food_items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("recommended_foods", "foods", "recommendations", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    if any(key in payload for key in ("name", "food", "food_name")):
        return [payload]

    return []


def _find_text_food_match(text: str, food_name: str) -> float | None:
    for pattern in _compiled_serving_patterns(food_name):
        match = pattern.search(text)
        if match:
            return _safe_float(match.group("servings"), 1.0)

    escaped = re.escape(food_name)
    if re.search(rf"\b{escaped}\b", text, flags=re.IGNORECASE):
        return 1.0
    return None


def _match_food_name(name: str, food_db: dict[str, FoodItem]) -> str | None:
    normalized = _normalize(name)
    for food_name in food_db:
        if _normalize(food_name) == normalized:
            return food_name
    token_signature = _token_signature(name)
    for food_name in food_db:
        if _token_signature(food_name) == token_signature:
            return food_name
    for food_name in food_db:
        if normalized in _normalize(food_name) or _normalize(food_name) in normalized:
            return food_name
    return None


def _dedupe_foods(
    foods: list[RecommendedFood],
    default_servings: float | None = None,
) -> list[RecommendedFood]:
    by_name: dict[str, float] = {}
    for food in foods:
        servings = food.servings if food.servings > 0 else (default_servings or 1.0)
        by_name[food.name] = by_name.get(food.name, 0.0) + servings
    return [
        RecommendedFood(name=name, servings=servings)
        for name, servings in sorted(by_name.items())
    ]


def _safe_float(value: Any, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _token_signature(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    return " ".join(sorted(tokens))
