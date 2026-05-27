"""Audit prototype foods against locally downloaded USDA FDC CSV datasets."""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..config import DATA_DIR, RESULTS_DIR
from .audit_foods_against_usda import NUTRIENT_MAP, QUERY_OVERRIDES


DEFAULT_DATASET_DIR = DATA_DIR / "dataset"

DATASET_PRIORITY = {
    "sr_legacy": 1,
    "foundation": 2,
    "survey": 3,
    "branded": 4,
}

PROCESSED_IDS = {
    "F014", "F015", "F036", "F039", "F043", "F044", "F045", "F046",
    "F047", "F048", "F049", "F050", "F051", "F052", "F054",
}

QUERY_KEYWORDS = {
    name: set(query.split())
    for name, query in QUERY_OVERRIDES.items()
}

STATE_TOKENS = {
    "raw", "cooked", "baked", "boiled", "drained", "roasted", "fried",
    "with", "without", "salt", "skin", "flesh", "whole", "plain", "low",
    "sodium", "water",
}

FOOD_SPECIFIC_EXCLUDED_TERMS = {
    "Banana": {"pepper", "pudding", "chips", "melon", "smoothie", "bar", "juice"},
    "Apple": {"mammy", "mamey", "juice", "pie", "sauce"},
    "Broccoli": {"raab"},
    "Spinach": {"malabar"},
    "Tomato": {"yam", "juice", "sauce", "paste", "powder", "sun", "dried"},
    "Carrot": {"yam", "juice", "cake"},
    "Orange": {"peel", "juice", "carrot", "pineapple"},
    "Orange juice": {"pineapple", "blend"},
    "Potato baked": {"sweet"},
    "Bagel": {"chips", "pizza"},
    "Milk low-fat": {"chocolate"},
    "Sugary cereal": {"bar"},
}

CORE_TOKEN_OVERRIDES = {
    "Brown rice": {"rice", "brown"},
    "White rice": {"rice", "white"},
    "Whole wheat bread": {"bread", "wheat"},
    "Whole wheat pasta": {"pasta", "wheat"},
    "Sweet potato baked": {"sweet", "potato"},
    "Potato baked": {"potato"},
    "Orange juice": {"orange", "juice"},
    "Chicken breast": {"chicken", "breast"},
    "Turkey breast": {"turkey", "breast"},
    "Pork tenderloin": {"pork", "tenderloin"},
    "Black beans cooked": {"black", "bean"},
    "Peanut butter": {"peanut", "butter"},
    "Pepperoni pizza": {"pepperoni", "pizza"},
    "Potato chips": {"potato", "chips"},
    "Chocolate cake": {"chocolate", "cake"},
    "Tuna canned in water": {"tuna"},
}

NEGATIVE_TERMS = {
    "baby", "infant", "restaurant", "school", "fast", "mcdonald", "burger king",
    "wendy", "kfc", "subway",
}


@dataclass(frozen=True)
class DatasetSpec:
    label: str
    root: Path
    food_csv: Path
    food_nutrient_csv: Path
    nutrient_csv: Path
    priority: int


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--foods-csv", default=str(DATA_DIR / "foods_extended.csv"))
    parser.add_argument("--output-json", default="usda_local_food_audit_55.json")
    parser.add_argument("--output-md", default="usda_local_food_audit_55.md")
    parser.add_argument("--candidate-review-md", default="usda_local_food_candidates_55.md")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--include-branded",
        action="store_true",
        help="Include the very large Branded Food dataset in candidate search.",
    )
    parser.add_argument("--food-id", action="append")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    foods = _load_csv(Path(args.foods_csv))
    if args.food_id:
        requested = set(args.food_id)
        foods = [food for food in foods if food["food_id"] in requested]
    if args.limit is not None:
        foods = foods[: args.limit]

    specs = _discover_datasets(Path(args.dataset_dir), include_branded=args.include_branded)
    food_index = _load_food_index(specs)
    nutrient_index = _load_nutrient_index(specs)

    rows = []
    for food in foods:
        candidates = _rank_candidates(food, food_index, args.top_k)
        best = candidates[0] if candidates else None
        row = _audit_candidate(food, best, candidates, nutrient_index)
        rows.append(row)

    output = {
        "metadata": {
            "source": "Local USDA FoodData Central CSV datasets",
            "dataset_dir": str(Path(args.dataset_dir)),
            "foods_csv": str(Path(args.foods_csv)),
            "candidate_selection": "Token-overlap ranking over local food.csv descriptions with dataset priority tie-breaks.",
            "nutrient_basis": "Current CSV values are converted from per serving to per 100 g before comparison.",
            "limitations": [
                "Candidate selection is automatic and should be manually reviewed.",
                "Processed and composite foods may require branded labels or deliberately selected FNDDS entries.",
                "GI is not audited because USDA FDC does not provide GI as a standard nutrient field.",
            ],
        },
        "summary": _summarize(rows),
        "rows": rows,
    }

    json_path = _resolve_results_path(args.output_json)
    md_path = _resolve_results_path(args.output_md)
    candidate_review_path = _resolve_results_path(args.candidate_review_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_review_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(output), encoding="utf-8")
    candidate_review_path.write_text(_render_candidate_review(output), encoding="utf-8")
    print(f"Saved local USDA audit JSON to {json_path}")
    print(f"Saved local USDA audit markdown to {md_path}")
    print(f"Saved candidate review markdown to {candidate_review_path}")
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))


def _discover_datasets(dataset_dir: Path, include_branded: bool) -> list[DatasetSpec]:
    specs = []
    for root in sorted(dataset_dir.iterdir()):
        if not root.is_dir():
            continue
        lower = root.name.lower()
        label = None
        for key in DATASET_PRIORITY:
            if key in lower:
                label = key
                break
        if label is None:
            continue
        if label == "branded" and not include_branded:
            continue
        food_csv = root / "food.csv"
        food_nutrient_csv = root / "food_nutrient.csv"
        nutrient_csv = root / "nutrient.csv"
        if food_csv.exists() and food_nutrient_csv.exists() and nutrient_csv.exists():
            specs.append(DatasetSpec(
                label=label,
                root=root,
                food_csv=food_csv,
                food_nutrient_csv=food_nutrient_csv,
                nutrient_csv=nutrient_csv,
                priority=DATASET_PRIORITY[label],
            ))
    if not specs:
        raise SystemExit(f"No USDA CSV datasets found under {dataset_dir}")
    return specs


def _load_food_index(specs: list[DatasetSpec]) -> list[dict]:
    foods = []
    for spec in specs:
        for row in _load_csv(spec.food_csv):
            description = row.get("description", "")
            tokens = _tokens(description)
            foods.append({
                "fdc_id": row["fdc_id"],
                "description": description,
                "data_type": row.get("data_type", ""),
                "publication_date": row.get("publication_date", ""),
                "dataset": spec.label,
                "dataset_priority": spec.priority,
                "tokens": tokens,
            })
    return foods


def _load_nutrient_index(specs: list[DatasetSpec]) -> dict[str, dict[int, float]]:
    wanted_ids = set()
    for meta in NUTRIENT_MAP.values():
        wanted_ids.update(meta["ids"])

    index: dict[str, dict[int, float]] = {}
    for spec in specs:
        for row in _load_csv(spec.food_nutrient_csv):
            nutrient_id = _int(row.get("nutrient_id"))
            if nutrient_id not in wanted_ids:
                continue
            amount = _float(row.get("amount"))
            if amount is None:
                continue
            index.setdefault(row["fdc_id"], {})[nutrient_id] = amount
    return index


def _rank_candidates(food: dict, food_index: list[dict], top_k: int) -> list[dict]:
    query = QUERY_OVERRIDES.get(food["name"], food["name"])
    query_tokens = QUERY_KEYWORDS.get(food["name"], _tokens(query))
    query_tokens = {_normalize_token(token) for token in query_tokens}
    required_tokens = _required_tokens(food["name"], query_tokens)
    is_processed = food["food_id"] in PROCESSED_IDS

    scored = []
    for candidate in food_index:
        score = _score_candidate(food["name"], query_tokens, required_tokens, candidate, is_processed)
        if score <= 0:
            continue
        scored.append({
            **candidate,
            "score": score,
            "query": query,
            "required_tokens": sorted(required_tokens),
        })
    scored.sort(key=lambda row: (-row["score"], row["dataset_priority"], len(row["description"])))
    return [
        {key: value for key, value in row.items() if key != "tokens"}
        for row in scored[:top_k]
    ]


def _score_candidate(
    food_name: str,
    query_tokens: set[str],
    required_tokens: set[str],
    candidate: dict,
    is_processed: bool,
) -> float:
    tokens = candidate["tokens"]
    if not query_tokens:
        return 0
    if required_tokens and not required_tokens.issubset(tokens):
        return 0
    overlap = len(query_tokens & tokens)
    if overlap == 0:
        return 0
    score = overlap / len(query_tokens)

    description = candidate["description"].lower()
    excluded_terms = FOOD_SPECIFIC_EXCLUDED_TERMS.get(food_name, set())
    excluded_hits = excluded_terms & tokens
    if excluded_hits:
        score -= 0.6 * len(excluded_hits)

    for term in NEGATIVE_TERMS:
        if term in description:
            score -= 0.3

    if required_tokens:
        score += len(required_tokens & tokens) / len(required_tokens)
    first_token = next(iter(_tokens(description)), "")
    if first_token in required_tokens:
        score += 0.2
    if "raw" in query_tokens and "raw" in tokens:
        score += 0.15
    if "cooked" in query_tokens and "cooked" in tokens:
        score += 0.15
    if "baked" in query_tokens and "baked" in tokens:
        score += 0.15
    if not is_processed and candidate["dataset"] == "branded":
        score -= 0.5
    if is_processed and candidate["dataset"] in {"survey", "branded"}:
        score += 0.1
    if candidate["dataset"] in {"sr_legacy", "foundation"} and not is_processed:
        score += 0.05
    return score


def _audit_candidate(
    food: dict,
    best: dict | None,
    candidates: list[dict],
    nutrient_index: dict[str, dict[int, float]],
) -> dict:
    if best is None:
        return {
            "food_id": food["food_id"],
            "name": food["name"],
            "status": "no_local_candidate",
            "candidates": candidates,
        }

    nutrients = nutrient_index.get(str(best["fdc_id"]), {})
    comparisons = []
    warning_fields = []
    missing_fields = []
    serving_size_g = _float(food.get("serving_size_g"))

    for field, meta in NUTRIENT_MAP.items():
        current_per_serving = _float(food.get(field))
        if current_per_serving is None or not serving_size_g:
            continue
        current_per_100g = current_per_serving / serving_size_g * 100
        usda_value = None
        for nutrient_id in meta["ids"]:
            if nutrient_id in nutrients:
                usda_value = nutrients[nutrient_id]
                break
        if usda_value is None:
            missing_fields.append(field)
            comparisons.append({
                "field": field,
                "current_per_100g": round(current_per_100g, 4),
                "usda_per_100g": None,
                "status": "missing_in_candidate",
            })
            continue
        diff = current_per_100g - usda_value
        relative_diff = None if usda_value == 0 else diff / usda_value
        status = _comparison_status(field, diff, relative_diff)
        if status == "warning":
            warning_fields.append(field)
        comparisons.append({
            "field": field,
            "current_per_100g": round(current_per_100g, 4),
            "usda_per_100g": round(usda_value, 4),
            "diff": round(diff, 4),
            "relative_diff": None if relative_diff is None else round(relative_diff, 4),
            "status": status,
        })

    if warning_fields:
        status = "matched_with_warnings"
    else:
        status = "matched_no_major_warnings"

    return {
        "food_id": food["food_id"],
        "name": food["name"],
        "status": status,
        "selected_candidate": {
            "fdc_id": best["fdc_id"],
            "description": best["description"],
            "data_type": best["data_type"],
            "dataset": best["dataset"],
            "publication_date": best["publication_date"],
            "score": round(best["score"], 4),
            "query": best["query"],
        },
        "warning_fields": warning_fields,
        "missing_fields": missing_fields,
        "comparisons": comparisons,
        "top_candidates": candidates,
    }


def _comparison_status(field: str, diff: float, relative_diff: float | None) -> str:
    abs_diff = abs(diff)
    if field.endswith("_mg"):
        if abs_diff <= 5:
            return "ok"
        if relative_diff is not None and abs(relative_diff) <= 0.25:
            return "ok"
        return "warning"
    if abs_diff <= 1:
        return "ok"
    if relative_diff is not None and abs(relative_diff) <= 0.25:
        return "ok"
    return "warning"


def _summarize(rows: list[dict]) -> dict:
    return {
        "food_count": len(rows),
        "matched_no_major_warnings": sum(1 for row in rows if row["status"] == "matched_no_major_warnings"),
        "matched_with_warnings": sum(1 for row in rows if row["status"] == "matched_with_warnings"),
        "no_local_candidate": sum(1 for row in rows if row["status"] == "no_local_candidate"),
        "rows_with_missing_fields": sum(1 for row in rows if row.get("missing_fields")),
    }


def _render_markdown(output: dict) -> str:
    lines = [
        "# Local USDA FoodData Central Audit",
        "",
        "This audit uses locally downloaded USDA FoodData Central CSV files. It does not call the API.",
        "",
        "Important: candidate selection is automatic and must be manually reviewed before claiming source-level accuracy.",
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
        "| Food ID | Name | Status | FDC ID | Dataset | Selected USDA description | Warning fields | Missing fields |",
        "|---|---|---|---:|---|---|---|---|",
    ])
    for row in output["rows"]:
        selected = row.get("selected_candidate", {})
        lines.append(
            "| "
            f"{row.get('food_id', '')} | "
            f"{row.get('name', '')} | "
            f"{row.get('status', '')} | "
            f"{selected.get('fdc_id', '')} | "
            f"{selected.get('dataset', '')} | "
            f"{_escape(selected.get('description', ''))} | "
            f"{', '.join(row.get('warning_fields', [])) or 'none'} | "
            f"{', '.join(row.get('missing_fields', [])) or 'none'} |"
        )

    lines.extend([
        "",
        "## Review Guidance",
        "",
        "- Use `matched_no_major_warnings` as a candidate for source mapping, not final proof.",
        "- Manually review selected candidate descriptions, especially for raw/cooked state and processed foods.",
        "- For `matched_with_warnings`, inspect warning nutrients before using the values as publication-grade food composition data.",
        "- GI is not audited because USDA FDC does not provide GI as a standard nutrient field.",
        "",
    ])
    return "\n".join(lines)


def _render_candidate_review(output: dict) -> str:
    lines = [
        "# USDA Candidate Review",
        "",
        "This file lists the top local USDA FoodData Central candidates for manual review.",
        "Use it to choose source identifiers; do not treat automatic rank 1 as final evidence.",
        "",
    ]
    for row in output["rows"]:
        selected = row.get("selected_candidate", {})
        lines.extend([
            f"## {row.get('food_id', '')} {row.get('name', '')}",
            "",
            f"- Current status: `{row.get('status', '')}`",
            f"- Selected candidate: `{selected.get('fdc_id', '')}` {selected.get('description', '')}",
            f"- Warning fields: {', '.join(row.get('warning_fields', [])) or 'none'}",
            f"- Missing fields: {', '.join(row.get('missing_fields', [])) or 'none'}",
            "",
            "| Rank | Score | FDC ID | Dataset | Description |",
            "|---:|---:|---:|---|---|",
        ])
        for rank, candidate in enumerate(row.get("top_candidates", []), start=1):
            lines.append(
                "| "
                f"{rank} | "
                f"{round(candidate.get('score', 0), 4)} | "
                f"{candidate.get('fdc_id', '')} | "
                f"{candidate.get('dataset', '')} | "
                f"{_escape(candidate.get('description', ''))} |"
            )
        lines.append("")
    return "\n".join(lines)


def _required_tokens(food_name: str, query_tokens: set[str]) -> set[str]:
    if food_name in CORE_TOKEN_OVERRIDES:
        return CORE_TOKEN_OVERRIDES[food_name]
    core_tokens = {
        token
        for token in query_tokens
        if token not in STATE_TOKENS and len(token) > 2
    }
    return core_tokens or query_tokens


def _tokens(text: str) -> set[str]:
    return {
        _normalize_token(token)
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in {"and", "or", "with", "without", "the", "as", "nfs", "ns"}
    }


def _normalize_token(token: str) -> str:
    irregular = {
        "tomatoes": "tomato",
        "potatoes": "potato",
        "strawberries": "strawberry",
        "blueberries": "blueberry",
        "chickpeas": "chickpea",
        "grapes": "grape",
        "mushrooms": "mushroom",
        "carrots": "carrot",
        "oranges": "orange",
        "bananas": "banana",
        "almonds": "almond",
        "lentils": "lentil",
        "crackers": "cracker",
        "cookies": "cookie",
        "bagels": "bagel",
        "beans": "bean",
        "oats": "oat",
        "cereals": "cereal",
    }
    if token in irregular:
        return irregular[token]
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _resolve_results_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else RESULTS_DIR / path


if __name__ == "__main__":
    main()
