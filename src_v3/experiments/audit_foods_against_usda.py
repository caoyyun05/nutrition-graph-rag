"""Audit prototype food nutrient values against USDA FoodData Central."""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..config import DATA_DIR, RESULTS_DIR


NUTRIENT_MAP = {
    "energy_kcal": {"ids": {1008}, "unit": "kcal"},
    "protein_g": {"ids": {1003}, "unit": "g"},
    "carbohydrate_g": {"ids": {1005}, "unit": "g"},
    "fat_g": {"ids": {1004}, "unit": "g"},
    "fiber_g": {"ids": {1079}, "unit": "g"},
    "sodium_mg": {"ids": {1093}, "unit": "mg"},
    "potassium_mg": {"ids": {1092}, "unit": "mg"},
    "phosphorus_mg": {"ids": {1091}, "unit": "mg"},
    "added_sugar_g": {"ids": {1235, 539}, "unit": "g"},
}


QUERY_OVERRIDES = {
    "Brown rice": "rice brown cooked",
    "Oatmeal": "oats cooked oatmeal",
    "Whole wheat bread": "bread whole wheat",
    "White rice": "rice white cooked",
    "Broccoli": "broccoli cooked",
    "Spinach": "spinach cooked",
    "Tomato": "tomato raw",
    "Banana": "banana raw",
    "Apple": "apple raw",
    "Chicken breast": "chicken breast cooked skinless",
    "Salmon": "salmon cooked",
    "Tofu": "tofu firm",
    "Lentils cooked": "lentils cooked",
    "Canned soup": "soup canned",
    "Low-sodium yogurt": "yogurt low sodium",
    "Quinoa cooked": "quinoa cooked",
    "Whole wheat pasta": "pasta whole wheat cooked",
    "Corn": "corn sweet cooked",
    "Potato baked": "potato baked flesh skin",
    "Sweet potato baked": "sweet potato baked",
    "Kale": "kale cooked",
    "Carrot": "carrot raw",
    "Cucumber": "cucumber raw",
    "Mushroom": "mushrooms raw",
    "Romaine lettuce": "lettuce romaine raw",
    "Orange": "orange raw",
    "Grapes": "grapes raw",
    "Strawberries": "strawberries raw",
    "Avocado": "avocado raw",
    "Orange juice": "orange juice",
    "Egg": "egg whole cooked",
    "Turkey breast": "turkey breast cooked",
    "Lean beef": "beef lean cooked",
    "Pork tenderloin": "pork tenderloin cooked",
    "Shrimp": "shrimp cooked",
    "Sardines canned": "sardines canned",
    "Milk low-fat": "milk lowfat",
    "Cheddar cheese": "cheese cheddar",
    "Cottage cheese": "cottage cheese",
    "Chickpeas cooked": "chickpeas cooked",
    "Black beans cooked": "black beans cooked",
    "Almonds": "almonds raw",
    "Peanut butter": "peanut butter",
    "Ham": "ham",
    "Instant noodles": "instant noodles",
    "Pepperoni pizza": "pizza pepperoni",
    "Salted crackers": "saltine crackers",
    "Potato chips": "potato chips",
    "Soda": "carbonated beverage cola",
    "Cookies": "cookies",
    "Chocolate cake": "chocolate cake",
    "Sugary cereal": "breakfast cereal sweetened",
    "Bagel": "bagel plain",
    "Tuna canned in water": "tuna canned water",
    "Edamame": "edamame cooked",
}


@dataclass(frozen=True)
class AuditThresholds:
    relative_warn: float = 0.25
    absolute_warn: float = 5.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--foods-csv", default=str(DATA_DIR / "foods_extended.csv"))
    parser.add_argument("--output-json", default="usda_food_audit.json")
    parser.add_argument("--output-md", default="usda_food_audit.md")
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--api-key", default=os.getenv("FDC_API_KEY", "DEMO_KEY"))
    parser.add_argument("--data-type", action="append", default=["SR Legacy", "Foundation", "Survey (FNDDS)"])
    parser.add_argument("--page-size", type=int, default=5)
    parser.add_argument("--limit", type=int, help="Audit only the first N foods.")
    parser.add_argument("--food-id", action="append", help="Audit only selected food IDs.")
    args = parser.parse_args()

    foods = _load_foods(Path(args.foods_csv))
    if args.food_id:
        requested = set(args.food_id)
        foods = [food for food in foods if food["food_id"] in requested]
    if args.limit is not None:
        foods = foods[: args.limit]

    rows = []
    for index, food in enumerate(foods, start=1):
        query = QUERY_OVERRIDES.get(food["name"], food["name"])
        print(f"[{index}/{len(foods)}] Searching USDA FDC for {food['food_id']} {food['name']} -> {query}")
        try:
            candidate = _search_food(
                query=query,
                api_key=args.api_key,
                data_types=args.data_type,
                page_size=args.page_size,
            )
            row = _audit_food(food, query, candidate)
        except Exception as exc:  # noqa: BLE001 - preserve diagnostic in audit output
            row = {
                "food_id": food["food_id"],
                "name": food["name"],
                "query": query,
                "status": "api_or_match_error",
                "error": str(exc),
            }
        rows.append(row)
        if args.sleep_seconds > 0 and index < len(foods):
            time.sleep(args.sleep_seconds)

    summary = _summarize(rows)
    output = {
        "metadata": {
            "source": "USDA FoodData Central",
            "api_key_mode": "provided_or_demo",
            "foods_csv": str(Path(args.foods_csv)),
            "nutrient_basis": "Current CSV values converted from per serving to per 100 g before comparison.",
            "status_meaning": {
                "matched_with_warnings": "USDA candidate found, but one or more compared nutrients differ beyond thresholds.",
                "matched_no_major_warnings": "USDA candidate found and compared nutrients are within audit thresholds.",
                "api_or_match_error": "Search or API call failed.",
            },
        },
        "summary": summary,
        "rows": rows,
    }

    json_path = _resolve_results_path(args.output_json)
    md_path = _resolve_results_path(args.output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(output), encoding="utf-8")
    print(f"Saved USDA audit JSON to {json_path}")
    print(f"Saved USDA audit markdown to {md_path}")


def _load_foods(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _search_food(query: str, api_key: str, data_types: list[str], page_size: int) -> dict | None:
    params = {
        "query": query,
        "pageSize": str(page_size),
        "api_key": api_key,
    }
    for data_type in data_types:
        params.setdefault("dataType", [])
        params["dataType"].append(data_type)
    query_string = urllib.parse.urlencode(params, doseq=True)
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?{query_string}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    foods = payload.get("foods", [])
    if not foods:
        return None
    return foods[0]


def _audit_food(food: dict, query: str, candidate: dict | None) -> dict:
    if candidate is None:
        return {
            "food_id": food["food_id"],
            "name": food["name"],
            "query": query,
            "status": "no_usda_candidate",
        }

    nutrient_values = _candidate_nutrients(candidate)
    comparisons = []
    warnings = []
    serving_size_g = _float(food["serving_size_g"])
    thresholds = AuditThresholds()

    for field, meta in NUTRIENT_MAP.items():
        current_per_serving = _float(food.get(field, ""))
        if current_per_serving is None or serving_size_g in (None, 0):
            continue
        current_per_100g = current_per_serving / serving_size_g * 100
        usda_value = None
        for nutrient_id in meta["ids"]:
            if nutrient_id in nutrient_values:
                usda_value = nutrient_values[nutrient_id]
                break
        if usda_value is None:
            comparisons.append({
                "field": field,
                "current_per_100g": round(current_per_100g, 4),
                "usda_per_100g": None,
                "status": "missing_in_usda_candidate",
            })
            continue
        diff = current_per_100g - usda_value
        relative_diff = None if usda_value == 0 else diff / usda_value
        warn = _is_warning(diff, relative_diff, thresholds)
        if warn:
            warnings.append(field)
        comparisons.append({
            "field": field,
            "current_per_100g": round(current_per_100g, 4),
            "usda_per_100g": round(usda_value, 4),
            "diff": round(diff, 4),
            "relative_diff": None if relative_diff is None else round(relative_diff, 4),
            "status": "warning" if warn else "ok",
        })

    return {
        "food_id": food["food_id"],
        "name": food["name"],
        "query": query,
        "status": "matched_with_warnings" if warnings else "matched_no_major_warnings",
        "usda": {
            "fdc_id": candidate.get("fdcId"),
            "description": candidate.get("description"),
            "data_type": candidate.get("dataType"),
            "published_date": candidate.get("publishedDate"),
        },
        "warning_fields": warnings,
        "comparisons": comparisons,
    }


def _candidate_nutrients(candidate: dict) -> dict[int, float]:
    values = {}
    for nutrient in candidate.get("foodNutrients", []):
        nutrient_id = nutrient.get("nutrientId")
        value = nutrient.get("value")
        if nutrient_id is not None and value is not None:
            values[int(nutrient_id)] = float(value)
    return values


def _is_warning(diff: float, relative_diff: float | None, thresholds: AuditThresholds) -> bool:
    if abs(diff) <= thresholds.absolute_warn:
        return False
    if relative_diff is None:
        return abs(diff) > thresholds.absolute_warn
    return abs(relative_diff) > thresholds.relative_warn


def _float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _summarize(rows: list[dict]) -> dict:
    return {
        "food_count": len(rows),
        "matched_no_major_warnings": sum(1 for row in rows if row.get("status") == "matched_no_major_warnings"),
        "matched_with_warnings": sum(1 for row in rows if row.get("status") == "matched_with_warnings"),
        "no_usda_candidate": sum(1 for row in rows if row.get("status") == "no_usda_candidate"),
        "api_or_match_error": sum(1 for row in rows if row.get("status") == "api_or_match_error"),
    }


def _render_markdown(output: dict) -> str:
    lines = [
        "# USDA FoodData Central Audit",
        "",
        "This audit compares the prototype `foods_extended.csv` values against the first USDA FoodData Central candidate returned for each query.",
        "",
        "Important: this is a candidate-match audit, not a final human-reviewed food-composition validation. Food state, cooking method, brand, and serving definitions still need review.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in output["summary"].items():
        lines.append(f"| {key} | {value} |")

    lines.extend([
        "",
        "## Food-Level Results",
        "",
        "| Food ID | Name | Status | USDA FDC ID | USDA description | Warning fields |",
        "|---|---|---|---:|---|---|",
    ])
    for row in output["rows"]:
        usda = row.get("usda", {})
        lines.append(
            "| "
            f"{row.get('food_id', '')} | "
            f"{row.get('name', '')} | "
            f"{row.get('status', '')} | "
            f"{usda.get('fdc_id', '')} | "
            f"{_escape(usda.get('description', row.get('error', '')))} | "
            f"{', '.join(row.get('warning_fields', [])) or 'none'} |"
        )

    lines.extend([
        "",
        "## Interpretation",
        "",
        "- `matched_no_major_warnings` means the current prototype values are broadly close to the selected USDA candidate under the audit thresholds.",
        "- `matched_with_warnings` means at least one nutrient differs substantially and should be manually checked.",
        "- Processed foods and composite foods often require branded labels or a deliberately chosen generic FNDDS item.",
        "- GI values are not audited here because USDA FoodData Central generally does not provide GI as a standard nutrient field.",
        "",
    ])
    return "\n".join(lines)


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _resolve_results_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else RESULTS_DIR / path


if __name__ == "__main__":
    main()
