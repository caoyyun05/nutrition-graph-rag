"""Cypher queries for v2 clinical constraint graph."""

from __future__ import annotations

from .db import Neo4jClient


class ClinicalKGRepository:
    def __init__(self, db: Neo4jClient):
        self.db = db

    def get_food_constraints(self, diseases: list[str]) -> dict[str, list[dict]]:
        suitable = self.db.execute(
            """
            MATCH (f:Food)-[r:SUITABLE_FOR]->(d:Disease)
            WHERE d.name IN $diseases
            RETURN f.name AS name, f.category AS category, d.name AS disease,
                   r.reason AS reason, r.recommendation AS recommendation
            """,
            {"diseases": diseases},
        )
        contraindicated = self.db.execute(
            """
            MATCH (f:Food)-[r:CONTRAINDICATED]->(d:Disease)
            WHERE d.name IN $diseases
            RETURN f.name AS name, f.category AS category, d.name AS disease,
                   r.reason AS reason, r.warning AS warning, r.severity AS severity
            """,
            {"diseases": diseases},
        )
        return {"suitable_foods": suitable, "contraindicated_foods": contraindicated}

    def get_nutrient_constraints(self, diseases: list[str]) -> list[dict]:
        return self.db.execute(
            """
            MATCH (d:Disease)-[:HAS_CONSTRAINT]->(c:NutrientConstraint)
                  -[:CONSTRAINT_ON]->(n:Nutrient),
                  (c)-[:DERIVED_FROM]->(g:ClinicalGuideline)
            WHERE d.name IN $diseases
            RETURN c.constraint_id AS constraint_id,
                   d.name AS disease,
                   n.name AS nutrient,
                   c.lower_bound AS lower_bound,
                   c.upper_bound AS upper_bound,
                   c.unit AS unit,
                   c.condition AS condition,
                   c.constraint_type AS constraint_type,
                   c.priority AS priority,
                   g.guideline_id AS guideline_id,
                   g.name AS source,
                   c.note AS note
            """,
            {"diseases": diseases},
        )

    def get_food_nutrients(self, food_names: list[str]) -> list[dict]:
        return self.db.execute(
            """
            MATCH (f:Food)
            WHERE f.name IN $food_names
            OPTIONAL MATCH (f)-[r:CONTAINS]->(n:Nutrient)
            RETURN f.name AS food,
                   f.serving_size_g AS serving_size_g,
                   collect({
                       nutrient: n.name,
                       amount: r.amount,
                       unit: r.unit
                   }) AS nutrients
            """,
            {"food_names": food_names},
        )

