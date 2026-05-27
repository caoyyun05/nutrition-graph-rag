"""Smoke tests for deterministic LLM food extraction."""

from __future__ import annotations

from ..config import DATA_DIR
from ..csv_loader import load_foods
from ..llm_food_extractor import extract_recommended_foods


def main() -> None:
    foods = load_foods(DATA_DIR / "foods_extended.csv")

    json_text = """
    {
      "recommended_foods": [
        {"name": "Brown rice", "servings": 2},
        {"food": "Broccoli", "quantity": 3},
        {"food_name": "Unknown food", "servings": 1}
      ]
    }
    """
    json_result = extract_recommended_foods(json_text, foods)
    assert json_result["extraction_method"] == "json"
    assert _servings(json_result, "Brown rice") == 2
    assert _servings(json_result, "Broccoli") == 3
    assert json_result["unmatched_items"] == ["Unknown food"]

    text = "For dinner: Brown rice:2, Broccoli (3 servings), and 1 serving of Chicken breast."
    text_result = extract_recommended_foods(text, foods)
    assert text_result["extraction_method"] == "text_match"
    assert _servings(text_result, "Brown rice") == 2
    assert _servings(text_result, "Broccoli") == 3
    assert _servings(text_result, "Chicken breast") == 1

    plain_text = "A simple option is oatmeal with apple and low-sodium yogurt."
    plain_result = extract_recommended_foods(plain_text, foods)
    names = {food.name for food in plain_result["recommended_foods"]}
    assert {"Oatmeal", "Apple", "Low-sodium yogurt"} <= names

    print("v2 extraction smoke test passed")


def _servings(result: dict, name: str) -> float:
    for food in result["recommended_foods"]:
        if food.name == name:
            return food.servings
    raise AssertionError(f"Missing extracted food: {name}")


if __name__ == "__main__":
    main()
