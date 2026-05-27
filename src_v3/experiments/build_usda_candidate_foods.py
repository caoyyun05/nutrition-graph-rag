"""Build a parallel 55-food candidate table from local USDA FDC CSV files."""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..config import DATA_DIR, ROOT_DIR
from .audit_foods_against_usda import NUTRIENT_MAP
from .audit_foods_against_usda_local import _normalize_token


DATASET_DIR = DATA_DIR / "dataset"
OUTPUT_DIR = ROOT_DIR / "data_usda_55"

MANUAL_FDC_OVERRIDES = {
    "U001": "169704",
    "U002": "173905",
    "U003": "172688",
    "U005": "169967",
    "U006": "168463",
    "U007": "170457",
    "U009": "171688",
    "U020": "168483",
    "U024": "169251",
    "U027": "2709237",
    "U030": "169098",
    "U037": "170872",
    "U039": "172182",
    "U045": "2709153",
    "U051": "2707868",
}

FNDDS_NUTRIENT_ID_MAP = {
    "energy_kcal": {208},
    "protein_g": {203},
    "carbohydrate_g": {205},
    "fat_g": {204},
    "fiber_g": {291},
    "sodium_mg": {307},
    "potassium_mg": {306},
    "phosphorus_mg": {305},
    "added_sugar_g": {539},
}

NUTRIENT_IDS_BY_FIELD = {
    field: set(meta["ids"]) | FNDDS_NUTRIENT_ID_MAP.get(field, set())
    for field, meta in NUTRIENT_MAP.items()
}

DATASET_PRIORITY = {
    "sr_legacy": 1,
    "foundation": 2,
    "survey": 3,
}

NATURAL_CATEGORIES = {"grain", "vegetable", "fruit", "protein", "dairy", "legume"}

MANUAL_REVIEW_NOTES = {
    "U049": "Selected soda entry is cream soda. It is acceptable as sugar-sweetened soda, but not specifically cola.",
    "U052": "Selected sweetened cereal is a specific branded ready-to-eat cereal. This is acceptable for a high-sugar cereal case but should be described as a USDA candidate entry.",
}

TARGET_FOODS = [
    {"food_id": "U001", "name": "Brown rice", "category": "grain", "serving_size_g": 150, "query": "rice brown cooked", "required": ["rice", "brown"], "avoid": ["white", "uncle", "ben", "baby", "sausage", "link", "pork"]},
    {"food_id": "U002", "name": "Oatmeal", "category": "grain", "serving_size_g": 40, "query": "oats oatmeal cooked", "required": ["oat"], "avoid": ["cookie", "bar", "baby"]},
    {"food_id": "U003", "name": "Whole wheat bread", "category": "grain", "serving_size_g": 60, "query": "bread whole wheat", "required": ["bread", "wheat"], "avoid": ["pita", "baby"]},
    {"food_id": "U004", "name": "White rice", "category": "grain", "serving_size_g": 150, "query": "rice white cooked", "required": ["rice", "white"], "avoid": ["brown", "baby"]},
    {"food_id": "U005", "name": "Broccoli", "category": "vegetable", "serving_size_g": 100, "query": "broccoli cooked", "required": ["broccoli"], "avoid": ["raab", "baby"]},
    {"food_id": "U006", "name": "Spinach", "category": "vegetable", "serving_size_g": 100, "query": "spinach cooked", "required": ["spinach"], "avoid": ["malabar", "baby", "spaghetti", "pasta"]},
    {"food_id": "U007", "name": "Tomato", "category": "vegetable", "serving_size_g": 120, "query": "tomato raw", "required": ["tomato"], "avoid": ["sauce", "juice", "paste", "dried", "baby"]},
    {"food_id": "U008", "name": "Banana", "category": "fruit", "serving_size_g": 120, "query": "banana raw", "required": ["banana"], "avoid": ["pepper", "pudding", "chip", "melon", "bar", "smoothie", "baby"]},
    {"food_id": "U009", "name": "Apple", "category": "fruit", "serving_size_g": 150, "query": "apple raw", "required": ["apple"], "avoid": ["mammy", "mamey", "custard", "juice", "pie", "sauce", "baby"]},
    {"food_id": "U010", "name": "Chicken breast", "category": "protein", "serving_size_g": 100, "query": "chicken breast cooked skinless", "required": ["chicken", "breast"], "avoid": ["restaurant", "sandwich"]},
    {"food_id": "U011", "name": "Salmon", "category": "protein", "serving_size_g": 100, "query": "salmon cooked", "required": ["salmon"], "avoid": ["smoked", "spread"]},
    {"food_id": "U012", "name": "Tofu", "category": "protein", "serving_size_g": 100, "query": "tofu firm", "required": ["tofu"], "avoid": ["dessert"]},
    {"food_id": "U013", "name": "Lentils cooked", "category": "legume", "serving_size_g": 100, "query": "lentils cooked", "required": ["lentil"], "avoid": ["sprouted"]},
    {"food_id": "U014", "name": "Canned soup", "category": "processed", "serving_size_g": 250, "query": "soup canned", "required": ["soup"], "prefer_dataset": "survey", "avoid": ["dry"]},
    {"food_id": "U015", "name": "Low-fat yogurt", "category": "dairy", "serving_size_g": 170, "query": "yogurt low fat plain", "required": ["yogurt"], "avoid": ["frozen", "drink", "baby"]},
    {"food_id": "U016", "name": "Quinoa cooked", "category": "grain", "serving_size_g": 150, "query": "quinoa cooked", "required": ["quinoa"], "avoid": ["baby"]},
    {"food_id": "U017", "name": "Whole wheat pasta", "category": "grain", "serving_size_g": 140, "query": "pasta whole wheat cooked", "required": ["pasta", "wheat"], "avoid": ["lasagna"]},
    {"food_id": "U018", "name": "Corn", "category": "grain", "serving_size_g": 100, "query": "corn sweet cooked", "required": ["corn"], "avoid": ["meal", "flour", "baby"]},
    {"food_id": "U019", "name": "Potato baked", "category": "vegetable", "serving_size_g": 173, "query": "potato baked", "required": ["potato"], "avoid": ["sweet", "chip"]},
    {"food_id": "U020", "name": "Sweet potato baked", "category": "vegetable", "serving_size_g": 130, "query": "sweet potato baked", "required": ["sweet", "potato"], "avoid": ["chip"]},
    {"food_id": "U021", "name": "Kale", "category": "vegetable", "serving_size_g": 100, "query": "kale cooked", "required": ["kale"], "avoid": ["baby"]},
    {"food_id": "U022", "name": "Carrot", "category": "vegetable", "serving_size_g": 100, "query": "carrot raw", "required": ["carrot"], "avoid": ["juice", "cake", "baby"]},
    {"food_id": "U023", "name": "Cucumber", "category": "vegetable", "serving_size_g": 100, "query": "cucumber raw", "required": ["cucumber"], "avoid": ["pickle"]},
    {"food_id": "U024", "name": "Mushroom", "category": "vegetable", "serving_size_g": 100, "query": "mushrooms raw", "required": ["mushroom"], "avoid": ["soup"]},
    {"food_id": "U025", "name": "Romaine lettuce", "category": "vegetable", "serving_size_g": 85, "query": "lettuce romaine raw", "required": ["lettuce", "romaine"], "avoid": ["salad"]},
    {"food_id": "U026", "name": "Orange", "category": "fruit", "serving_size_g": 140, "query": "orange raw", "required": ["orange"], "avoid": ["peel", "juice", "pineapple", "baby"]},
    {"food_id": "U027", "name": "Grapes", "category": "fruit", "serving_size_g": 150, "query": "grapes raw", "required": ["grape"], "avoid": ["juice", "raisin", "leave"]},
    {"food_id": "U028", "name": "Strawberries", "category": "fruit", "serving_size_g": 150, "query": "strawberries raw", "required": ["strawberry"], "avoid": ["juice", "jam"]},
    {"food_id": "U029", "name": "Avocado", "category": "fruit", "serving_size_g": 100, "query": "avocado raw", "required": ["avocado"], "avoid": ["dip"]},
    {"food_id": "U030", "name": "Orange juice", "category": "fruit", "serving_size_g": 240, "query": "orange juice", "required": ["orange", "juice"], "avoid": ["pineapple", "carrot", "blend"]},
    {"food_id": "U031", "name": "Egg", "category": "protein", "serving_size_g": 50, "query": "egg whole cooked", "required": ["egg"], "avoid": ["substitute"]},
    {"food_id": "U032", "name": "Turkey breast", "category": "protein", "serving_size_g": 100, "query": "turkey breast cooked", "required": ["turkey", "breast"], "avoid": ["deli", "sandwich"]},
    {"food_id": "U033", "name": "Lean beef", "category": "protein", "serving_size_g": 100, "query": "beef lean cooked", "required": ["beef", "lean"], "avoid": ["restaurant"]},
    {"food_id": "U034", "name": "Pork tenderloin", "category": "protein", "serving_size_g": 100, "query": "pork tenderloin cooked", "required": ["pork", "tenderloin"], "avoid": ["restaurant"]},
    {"food_id": "U035", "name": "Shrimp", "category": "protein", "serving_size_g": 100, "query": "shrimp cooked", "required": ["shrimp"], "avoid": ["breaded"]},
    {"food_id": "U036", "name": "Sardines canned", "category": "protein", "serving_size_g": 100, "query": "sardines canned", "required": ["sardine"], "avoid": ["baby"]},
    {"food_id": "U037", "name": "Milk low-fat", "category": "dairy", "serving_size_g": 240, "query": "milk lowfat", "required": ["milk"], "avoid": ["chocolate", "evaporated", "dry"]},
    {"food_id": "U038", "name": "Cheddar cheese", "category": "dairy", "serving_size_g": 30, "query": "cheese cheddar", "required": ["cheese", "cheddar"], "avoid": ["sauce"]},
    {"food_id": "U039", "name": "Cottage cheese", "category": "dairy", "serving_size_g": 113, "query": "cottage cheese", "required": ["cottage", "cheese"], "avoid": ["baby"]},
    {"food_id": "U040", "name": "Chickpeas cooked", "category": "legume", "serving_size_g": 100, "query": "chickpeas cooked", "required": ["chickpea"], "avoid": ["hummus"]},
    {"food_id": "U041", "name": "Black beans cooked", "category": "legume", "serving_size_g": 100, "query": "black beans cooked", "required": ["black", "bean"], "avoid": ["soup"]},
    {"food_id": "U042", "name": "Almonds", "category": "legume", "serving_size_g": 28, "query": "almonds raw", "required": ["almond"], "avoid": ["butter", "milk"]},
    {"food_id": "U043", "name": "Peanut butter", "category": "legume", "serving_size_g": 32, "query": "peanut butter", "required": ["peanut", "butter"], "avoid": ["cookie"]},
    {"food_id": "U044", "name": "Ham", "category": "processed", "serving_size_g": 85, "query": "ham", "required": ["ham"], "prefer_dataset": "survey", "avoid": ["sandwich"]},
    {"food_id": "U045", "name": "Ramen noodles", "category": "processed", "serving_size_g": 85, "query": "ramen noodles", "required": ["ramen"], "prefer_dataset": "survey", "avoid": ["pudding"]},
    {"food_id": "U046", "name": "Pepperoni pizza", "category": "processed", "serving_size_g": 140, "query": "pizza pepperoni", "required": ["pizza", "pepperoni"], "prefer_dataset": "survey", "avoid": ["bagel"]},
    {"food_id": "U047", "name": "Salted crackers", "category": "processed", "serving_size_g": 30, "query": "saltine crackers", "required": ["cracker"], "prefer_dataset": "survey", "avoid": ["cheese"]},
    {"food_id": "U048", "name": "Potato chips", "category": "processed", "serving_size_g": 28, "query": "potato chips", "required": ["potato", "chip"], "prefer_dataset": "survey", "avoid": ["sweet"]},
    {"food_id": "U049", "name": "Soda", "category": "beverage", "serving_size_g": 355, "query": "carbonated beverage cola", "required": ["carbonated", "beverage"], "avoid": ["low", "diet", "saccharin"]},
    {"food_id": "U050", "name": "Cookies", "category": "processed", "serving_size_g": 45, "query": "cookies", "required": ["cookie"], "prefer_dataset": "survey", "avoid": ["protein"]},
    {"food_id": "U051", "name": "Chocolate cake", "category": "processed", "serving_size_g": 80, "query": "chocolate cake", "required": ["chocolate", "cake"], "prefer_dataset": "survey", "avoid": ["snack"]},
    {"food_id": "U052", "name": "Sweetened cereal", "category": "grain", "serving_size_g": 40, "query": "breakfast cereal sweetened", "required": ["cereal"], "avoid": ["bar", "baby"]},
    {"food_id": "U053", "name": "Bagel", "category": "grain", "serving_size_g": 100, "query": "bagel plain", "required": ["bagel"], "avoid": ["chip", "pizza"]},
    {"food_id": "U054", "name": "Tuna canned in water", "category": "protein", "serving_size_g": 100, "query": "tuna canned water", "required": ["tuna"], "avoid": ["salad", "sandwich"]},
    {"food_id": "U055", "name": "Edamame", "category": "legume", "serving_size_g": 100, "query": "edamame cooked", "required": ["edamame"], "avoid": []},
]

GI_PROXY = {
    "Brown rice": (50, "estimated_from_legacy_table"),
    "Oatmeal": (55, "estimated_from_legacy_table"),
    "Whole wheat bread": (50, "estimated_from_legacy_table"),
    "White rice": (83, "estimated_from_legacy_table"),
    "Broccoli": (15, "category_proxy_nonstarchy_vegetable"),
    "Spinach": (15, "category_proxy_nonstarchy_vegetable"),
    "Tomato": (15, "category_proxy_nonstarchy_vegetable"),
    "Banana": (51, "estimated_from_legacy_table"),
    "Apple": (36, "estimated_from_legacy_table"),
    "Chicken breast": (0, "non_carbohydrate_food_proxy"),
    "Salmon": (0, "non_carbohydrate_food_proxy"),
    "Tofu": (15, "category_proxy_legume_soy"),
    "Lentils cooked": (32, "estimated_from_legacy_table"),
    "Canned soup": (60, "category_proxy_composite_processed"),
    "Low-fat yogurt": (35, "estimated_from_legacy_table"),
    "Quinoa cooked": (53, "estimated_from_legacy_table"),
    "Whole wheat pasta": (48, "estimated_from_legacy_table"),
    "Corn": (52, "estimated_from_legacy_table"),
    "Potato baked": (85, "estimated_from_legacy_table"),
    "Sweet potato baked": (61, "estimated_from_legacy_table"),
    "Kale": (15, "category_proxy_nonstarchy_vegetable"),
    "Carrot": (39, "estimated_from_legacy_table"),
    "Cucumber": (15, "category_proxy_nonstarchy_vegetable"),
    "Mushroom": (15, "category_proxy_nonstarchy_vegetable"),
    "Romaine lettuce": (15, "category_proxy_nonstarchy_vegetable"),
    "Orange": (43, "estimated_from_legacy_table"),
    "Grapes": (53, "estimated_from_legacy_table"),
    "Strawberries": (40, "estimated_from_legacy_table"),
    "Avocado": (15, "category_proxy_low_carb_fruit"),
    "Orange juice": (50, "estimated_from_legacy_table"),
    "Egg": (0, "non_carbohydrate_food_proxy"),
    "Turkey breast": (0, "non_carbohydrate_food_proxy"),
    "Lean beef": (0, "non_carbohydrate_food_proxy"),
    "Pork tenderloin": (0, "non_carbohydrate_food_proxy"),
    "Shrimp": (0, "non_carbohydrate_food_proxy"),
    "Sardines canned": (0, "non_carbohydrate_food_proxy"),
    "Milk low-fat": (30, "estimated_from_legacy_table"),
    "Cheddar cheese": (0, "non_carbohydrate_food_proxy"),
    "Cottage cheese": (10, "category_proxy_dairy_low_carb"),
    "Chickpeas cooked": (28, "estimated_from_legacy_table"),
    "Black beans cooked": (30, "estimated_from_legacy_table"),
    "Almonds": (15, "category_proxy_nut"),
    "Peanut butter": (14, "estimated_from_legacy_table"),
    "Ham": (0, "non_carbohydrate_food_proxy"),
    "Ramen noodles": (70, "estimated_from_legacy_table"),
    "Pepperoni pizza": (60, "category_proxy_composite_processed"),
    "Salted crackers": (74, "estimated_from_legacy_table"),
    "Potato chips": (56, "estimated_from_legacy_table"),
    "Soda": (63, "estimated_from_legacy_table"),
    "Cookies": (70, "category_proxy_sweet_baked_food"),
    "Chocolate cake": (60, "category_proxy_sweet_baked_food"),
    "Sweetened cereal": (75, "category_proxy_sweetened_cereal"),
    "Bagel": (72, "estimated_from_legacy_table"),
    "Tuna canned in water": (0, "non_carbohydrate_food_proxy"),
    "Edamame": (18, "estimated_from_legacy_table"),
}


@dataclass(frozen=True)
class DatasetSpec:
    label: str
    food_csv: Path
    food_nutrient_csv: Path
    priority: int


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", default=str(DATASET_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--top-k", type=int, default=8)
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    output_dir = Path(args.output_dir)
    specs = _discover_datasets(dataset_dir)
    food_index = _load_food_index(specs)
    nutrient_index = _load_nutrient_index(specs)

    foods_rows = []
    mapping_rows = []
    review_rows = []
    selected = []
    for target in TARGET_FOODS:
        candidates = _rank_candidates(target, food_index, args.top_k)
        if target["food_id"] in MANUAL_FDC_OVERRIDES:
            override_id = MANUAL_FDC_OVERRIDES[target["food_id"]]
            override_candidate = _candidate_by_fdc_id(food_index, override_id)
            candidates = [
                {
                    **override_candidate,
                    "score": 999.0,
                    "query": target["query"],
                    "selection": "manual_override",
                }
            ] + [candidate for candidate in candidates if candidate["fdc_id"] != override_id]
        if not candidates:
            raise SystemExit(f"No USDA candidate found for {target['food_id']} {target['name']}")
        best = candidates[0]
        selected.append({**target, "candidate": best, "top_candidates": candidates})
        nutrients = nutrient_index.get(best["fdc_id"], {})
        food_row, field_status = _build_food_row(target, best, nutrients)
        foods_rows.append(food_row)
        mapping_rows.append(_build_mapping_row(target, best, field_status))
        review_rows.append(_build_review_row(target, best, candidates, field_status))

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "foods_usda_55.csv", foods_rows, list(foods_rows[0]))
    _write_csv(output_dir / "food_source_mapping_usda_55.csv", mapping_rows, list(mapping_rows[0]))
    _write_csv(output_dir / "food_candidate_review_usda_55.csv", review_rows, list(review_rows[0]))
    (output_dir / "foods_usda_55_audit.md").write_text(
        _render_audit(selected, foods_rows, mapping_rows),
        encoding="utf-8",
    )
    (output_dir / "foods_usda_55_build.json").write_text(
        json.dumps({"foods": selected}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved USDA candidate dataset to {output_dir}")
    print(f"Food rows: {len(foods_rows)}")
    print(f"Rows with estimated GI: {sum(1 for row in mapping_rows if row['gi_status'] != 'source_measured')}")
    print(f"Rows with imputed added sugar: {sum(1 for row in mapping_rows if 'added_sugar_g' in row['imputed_fields'])}")


def _discover_datasets(dataset_dir: Path) -> list[DatasetSpec]:
    specs = []
    for root in sorted(dataset_dir.iterdir()):
        if not root.is_dir():
            continue
        lower = root.name.lower()
        label = next((key for key in DATASET_PRIORITY if key in lower), None)
        if label is None:
            continue
        food_csv = root / "food.csv"
        food_nutrient_csv = root / "food_nutrient.csv"
        if food_csv.exists() and food_nutrient_csv.exists():
            specs.append(DatasetSpec(
                label=label,
                food_csv=food_csv,
                food_nutrient_csv=food_nutrient_csv,
                priority=DATASET_PRIORITY[label],
            ))
    if not specs:
        raise SystemExit(f"No USDA datasets found under {dataset_dir}")
    return specs


def _load_food_index(specs: list[DatasetSpec]) -> list[dict]:
    rows = []
    for spec in specs:
        for row in _load_csv(spec.food_csv):
            description = row.get("description", "")
            rows.append({
                "fdc_id": row["fdc_id"],
                "description": description,
                "data_type": row.get("data_type", ""),
                "publication_date": row.get("publication_date", ""),
                "dataset": spec.label,
                "dataset_priority": spec.priority,
                "tokens": _tokens(description),
            })
    return rows


def _load_nutrient_index(specs: list[DatasetSpec]) -> dict[str, dict[int, float]]:
    wanted_ids = {
        nutrient_id
        for nutrient_ids in NUTRIENT_IDS_BY_FIELD.values()
        for nutrient_id in nutrient_ids
    }
    index: dict[str, dict[int, float]] = {}
    for spec in specs:
        for row in _load_csv(spec.food_nutrient_csv):
            nutrient_id = _int(row.get("nutrient_id"))
            if nutrient_id not in wanted_ids:
                continue
            amount = _float(row.get("amount"))
            if amount is not None:
                index.setdefault(row["fdc_id"], {})[nutrient_id] = amount
    return index


def _rank_candidates(target: dict, food_index: list[dict], top_k: int) -> list[dict]:
    query_tokens = _tokens(target["query"])
    required = {_normalize_token(token) for token in target["required"]}
    avoid = {_normalize_token(token) for token in target.get("avoid", [])}
    prefer_dataset = target.get("prefer_dataset")
    scored = []
    for candidate in food_index:
        tokens = candidate["tokens"]
        if required and not required.issubset(tokens):
            continue
        score = len(query_tokens & tokens) / max(len(query_tokens), 1)
        score += len(required & tokens) / max(len(required), 1)
        score -= len(avoid & tokens) * 0.8
        if prefer_dataset and candidate["dataset"] == prefer_dataset:
            score += 0.35
        if not prefer_dataset and candidate["dataset"] in {"sr_legacy", "foundation"}:
            score += 0.1
        if "raw" in query_tokens and "raw" in tokens:
            score += 0.15
        if "cooked" in query_tokens and "cooked" in tokens:
            score += 0.15
        if "baked" in query_tokens and "baked" in tokens:
            score += 0.15
        description = candidate["description"].lower()
        if any(term in description for term in ["babyfood", "infant", "restaurant", "fast foods"]):
            score -= 0.5
        if score <= 0:
            continue
        scored.append({**candidate, "score": round(score, 4), "query": target["query"]})
    scored.sort(key=lambda row: (-row["score"], row["dataset_priority"], len(row["description"])))
    return [{key: value for key, value in row.items() if key != "tokens"} for row in scored[:top_k]]


def _build_food_row(target: dict, candidate: dict, nutrients: dict[int, float]) -> tuple[dict, dict]:
    serving_size = float(target["serving_size_g"])
    row = {
        "food_id": target["food_id"],
        "name": target["name"],
        "category": target["category"],
        "serving_size_g": _fmt(serving_size),
    }
    field_status = {}
    for field, nutrient_ids in NUTRIENT_IDS_BY_FIELD.items():
        per_100g = None
        for nutrient_id in nutrient_ids:
            if nutrient_id in nutrients:
                per_100g = nutrients[nutrient_id]
                break
        status = "source_measured"
        if per_100g is None and field == "added_sugar_g" and target["category"] in NATURAL_CATEGORIES:
            per_100g = 0.0
            status = "imputed_zero_natural_food"
        elif per_100g is None:
            per_100g = 0.0
            status = "imputed_zero_missing_usda_field"
        row[field] = _fmt(per_100g * serving_size / 100)
        field_status[field] = status
    gi, gi_status = GI_PROXY[target["name"]]
    row["gi"] = _fmt(gi)
    field_status["gi"] = gi_status
    field_status["fdc_id"] = candidate["fdc_id"]
    return row, field_status


def _build_mapping_row(target: dict, candidate: dict, field_status: dict) -> dict:
    imputed_fields = [
        field for field, status in field_status.items()
        if status.startswith("imputed")
    ]
    return {
        "food_id": target["food_id"],
        "name": target["name"],
        "fdc_id": candidate["fdc_id"],
        "source_database": "USDA FoodData Central",
        "source_dataset": candidate["dataset"],
        "source_data_type": candidate["data_type"],
        "source_food_name": candidate["description"],
        "publication_date": candidate["publication_date"],
        "download_date": "2026-05-26",
        "match_status": "manual_override_candidate" if target["food_id"] in MANUAL_FDC_OVERRIDES else "automatic_candidate_needs_manual_review",
        "imputed_fields": ";".join(imputed_fields),
        "gi_value": str(GI_PROXY[target["name"]][0]),
        "gi_status": GI_PROXY[target["name"]][1],
        "notes": MANUAL_REVIEW_NOTES.get(target["food_id"], "Parallel USDA candidate dataset; legacy v2 table is unchanged."),
    }


def _build_review_row(target: dict, best: dict, candidates: list[dict], field_status: dict) -> dict:
    return {
        "food_id": target["food_id"],
        "name": target["name"],
        "query": target["query"],
        "selected_fdc_id": best["fdc_id"],
        "selected_dataset": best["dataset"],
        "selected_description": best["description"],
        "selected_score": best["score"],
        "selection": best.get("selection", "automatic_ranked_candidate"),
        "review_note": MANUAL_REVIEW_NOTES.get(target["food_id"], ""),
        "top_candidates": " || ".join(
            f"{row['fdc_id']} [{row['dataset']}] {row['description']}"
            for row in candidates
        ),
        "imputed_fields": ";".join(
            field for field, status in field_status.items() if status.startswith("imputed")
        ),
    }


def _render_audit(selected: list[dict], foods_rows: list[dict], mapping_rows: list[dict]) -> str:
    lines = [
        "# USDA 55 Candidate Food Dataset",
        "",
        "This is a parallel candidate dataset built from locally downloaded USDA FoodData Central CSV files.",
        "It does not overwrite `data_v2/foods_extended.csv`.",
        "",
        "## Scope",
        "",
        "- 55 foods selected to preserve the experimental coverage of sodium, potassium, phosphorus, carbohydrate, fiber, added sugar, and processed-food cases.",
        "- Source candidates are selected automatically and must be manually reviewed before manuscript-level claims.",
        "- GI is not a USDA FDC field. GI values are carried as proxies with explicit status labels and should not be treated as USDA-sourced measurements.",
        "",
        "## Summary",
        "",
        f"- Food rows: {len(foods_rows)}",
        f"- USDA source rows: {len(mapping_rows)}",
        f"- Rows with imputed added sugar: {sum(1 for row in mapping_rows if 'added_sugar_g' in row['imputed_fields'])}",
        f"- Rows with GI proxies: {len(mapping_rows)}",
        "",
        "## Selected Candidates",
        "",
        "| Food ID | Name | FDC ID | Dataset | USDA description | Imputed fields | GI status |",
        "|---|---|---:|---|---|---|---|",
    ]
    mapping_by_id = {row["food_id"]: row for row in mapping_rows}
    for item in selected:
        mapping = mapping_by_id[item["food_id"]]
        candidate = item["candidate"]
        lines.append(
            "| "
            f"{item['food_id']} | "
            f"{item['name']} | "
            f"{candidate['fdc_id']} | "
            f"{candidate['dataset']} | "
            f"{_escape(candidate['description'])} | "
            f"{mapping['imputed_fields'] or 'none'} | "
            f"{mapping['gi_status']} |"
        )
    review_notes = [row for row in mapping_rows if row["notes"] != "Parallel USDA candidate dataset; legacy v2 table is unchanged."]
    if review_notes:
        lines.extend([
            "",
            "## Manual Review Flags",
            "",
            "| Food ID | Name | Note |",
            "|---|---|---|",
        ])
        for row in review_notes:
            lines.append(f"| {row['food_id']} | {row['name']} | {_escape(row['notes'])} |")
    lines.extend([
        "",
        "## Next Checks",
        "",
        "1. Manually inspect candidate descriptions in `food_candidate_review_usda_55.csv`.",
        "2. Decide whether GI should remain a non-core proxy field or be supplemented from a dedicated GI source.",
        "3. Generate a separate USDA scenario file and rerun deterministic experiments before touching manuscript tables.",
        "",
    ])
    return "\n".join(lines)


def _tokens(text: str) -> set[str]:
    return {
        _normalize_token(token)
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in {"and", "or", "with", "without", "the", "as", "nfs", "ns"}
    }


def _candidate_by_fdc_id(food_index: list[dict], fdc_id: str) -> dict:
    for candidate in food_index:
        if candidate["fdc_id"] == fdc_id:
            return {key: value for key, value in candidate.items() if key != "tokens"}
    raise SystemExit(f"Manual FDC override not found in local food index: {fdc_id}")


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _fmt(value: float) -> str:
    rounded = round(value, 4)
    if rounded == int(rounded):
        return str(int(rounded))
    return str(rounded).rstrip("0").rstrip(".")


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    main()
