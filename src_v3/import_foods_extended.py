"""Import extended food data into Neo4j.

By default this module prints a dry-run summary. Use ``--write`` to execute
the import against the configured Neo4j database.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import DATA_DIR, load_neo4j_config
from .csv_loader import load_foods


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write rows to Neo4j instead of dry-run only.")
    parser.add_argument("--path", default=DATA_DIR / "foods_extended.csv")
    args = parser.parse_args()

    foods = load_foods(Path(args.path))
    if not args.write:
        print(f"Dry run: loaded {len(foods)} foods from {args.path}")
        return

    from .db import Neo4jClient

    query = """
    MERGE (f:Food {food_id: $food_id})
    SET f.name = $name,
        f.category = $category,
        f.serving_size_g = $serving_size_g
    WITH f, $nutrients AS nutrients
    UNWIND nutrients AS nutrient_row
    WITH f, nutrient_row
    WHERE nutrient_row.amount IS NOT NULL
    WITH f, nutrient_row.name AS nutrient_name, nutrient_row.amount AS amount, nutrient_row.unit AS unit
    MERGE (n:Nutrient {name: nutrient_name})
    MERGE (f)-[r:CONTAINS]->(n)
    SET r.amount = amount,
        r.unit = unit,
        r.basis = "per_serving"
    """
    with Neo4jClient(load_neo4j_config()) as db:
        for food in foods.values():
            db.execute(
                query,
                {
                    "food_id": food.food_id,
                    "name": food.name,
                    "category": food.category,
                    "serving_size_g": food.serving_size_g,
                    "nutrients": [
                        {
                            "name": nutrient,
                            "amount": amount,
                            "unit": _unit_for_nutrient(nutrient),
                        }
                        for nutrient, amount in food.nutrients.items()
                    ],
                },
            )
    print(f"Imported {len(foods)} foods into Neo4j")


def _unit_for_nutrient(nutrient: str) -> str:
    if nutrient.endswith("_mg"):
        return "mg/serving"
    if nutrient.endswith("_g"):
        return "g/serving"
    if nutrient.endswith("_kcal"):
        return "kcal/serving"
    return "value/serving"


if __name__ == "__main__":
    main()
