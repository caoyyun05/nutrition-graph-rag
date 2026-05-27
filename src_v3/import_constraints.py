"""Import clinical nutrient constraints into Neo4j."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import DATA_DIR, load_neo4j_config
from .csv_loader import load_constraints


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write rows to Neo4j instead of dry-run only.")
    parser.add_argument("--path", default=DATA_DIR / "nutrient_constraints.csv")
    args = parser.parse_args()

    constraints = load_constraints(Path(args.path))
    if not args.write:
        print(f"Dry run: loaded {len(constraints)} nutrient constraints from {args.path}")
        return

    from .db import Neo4jClient

    query = """
    MERGE (d:Disease {name: $disease})
    MERGE (n:Nutrient {name: $nutrient})
    MERGE (g:ClinicalGuideline {guideline_id: $guideline_id})
    SET g.name = $source
    MERGE (c:NutrientConstraint {constraint_id: $constraint_id})
    SET c.lower_bound = $lower_bound,
        c.upper_bound = $upper_bound,
        c.unit = $unit,
        c.condition = $condition,
        c.constraint_type = $constraint_type,
        c.priority = $priority,
        c.note = $note
    MERGE (d)-[:HAS_CONSTRAINT]->(c)
    MERGE (c)-[:CONSTRAINT_ON]->(n)
    MERGE (c)-[:DERIVED_FROM]->(g)
    WITH c, $risk_factors AS risk_factors
    UNWIND risk_factors AS risk_factor
    MERGE (r:RiskFactor {name: risk_factor})
    MERGE (r)-[:ACTIVATES]->(c)
    """
    with Neo4jClient(load_neo4j_config()) as db:
        for constraint in constraints:
            params = {
                **constraint.__dict__,
                "risk_factors": _risk_factors_for_condition(constraint.condition),
            }
            db.execute(query, params)
    print(f"Imported {len(constraints)} nutrient constraints into Neo4j")


def _risk_factors_for_condition(condition: str) -> list[str]:
    normalized = condition.lower()
    risk_factors: list[str] = []
    if "hyperkalemia" in normalized:
        risk_factors.append("hyperkalemia_risk")
    if "hyperphosphatemia" in normalized:
        risk_factors.append("hyperphosphatemia_risk")
    if "elevated_serum_phosphorus" in normalized or "elevated serum phosphorus" in normalized:
        risk_factors.append("elevated_serum_phosphorus")
    return risk_factors


if __name__ == "__main__":
    main()
