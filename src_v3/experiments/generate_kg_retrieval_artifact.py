"""Generate a reproducible KG retrieval artifact from the CSV-backed graph data."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ..config import DATA_DIR, RESULTS_DIR
from ..csv_loader import load_constraints, load_foods, select_active_constraints
from ..models import NutrientConstraint
from .scenarios import TestScenario, load_scenarios


QUERY_TEMPLATES = {
    "retrieve_constraints": """
MATCH (d:Disease)-[:HAS_CONSTRAINT]->(c:NutrientConstraint)
      -[:CONSTRAINT_ON]->(n:Nutrient),
      (c)-[:DERIVED_FROM]->(g:ClinicalGuideline)
WHERE d.name IN $diseases
RETURN d.name AS disease,
       c.constraint_id AS constraint_id,
       n.name AS nutrient,
       c.lower_bound AS lower_bound,
       c.upper_bound AS upper_bound,
       c.condition AS condition,
       c.priority AS priority,
       g.guideline_id AS guideline_id,
       g.name AS source
""".strip(),
    "retrieve_food_nutrients": """
MATCH (f:Food)-[r:CONTAINS]->(n:Nutrient)
WHERE f.name IN $food_names
RETURN f.name AS food,
       f.serving_size_g AS serving_size_g,
       collect({nutrient: n.name, amount: r.amount, unit: r.unit}) AS nutrients
""".strip(),
    "retrieve_guideline_provenance": """
MATCH (c:NutrientConstraint)-[:DERIVED_FROM]->(g:ClinicalGuideline)
WHERE c.constraint_id IN $constraint_ids
RETURN c.constraint_id AS constraint_id,
       g.guideline_id AS guideline_id,
       g.name AS source
""".strip(),
    "retrieve_risk_activated_constraints": """
MATCH (r:RiskFactor)-[:ACTIVATES]->(c:NutrientConstraint)
      <-[:HAS_CONSTRAINT]-(d:Disease)
WHERE d.name IN $diseases AND r.name IN $risk_factors
RETURN r.name AS risk_factor,
       d.name AS disease,
       c.constraint_id AS constraint_id,
       c.condition AS condition
""".strip(),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-id", default="S002")
    parser.add_argument("--output-json", default="kg_retrieval_artifact_s002.json")
    parser.add_argument("--output-md", default="kg_retrieval_artifact_s002.md")
    args = parser.parse_args()

    foods = load_foods(DATA_DIR / "foods_extended.csv")
    constraints = load_constraints(DATA_DIR / "nutrient_constraints.csv")
    scenarios = load_scenarios(DATA_DIR / "test_scenarios.csv")
    scenario = _find_scenario(scenarios, args.scenario_id)

    active_constraints = select_active_constraints(
        constraints,
        scenario.diseases,
        scenario.risk_factors,
    )
    recommended_names = [food.name for food in scenario.recommended_foods]
    food_rows = [
        {
            "food_id": foods[name].food_id,
            "name": foods[name].name,
            "category": foods[name].category,
            "serving_size_g": foods[name].serving_size_g,
            "nutrients": foods[name].nutrients,
        }
        for name in recommended_names
        if name in foods
    ]

    artifact = {
        "metadata": {
            "scenario_id": scenario.scenario_id,
            "scenario_name": scenario.name,
            "note": (
                "CSV-backed graph-compatible retrieval artifact. The same "
                "entities can be imported into Neo4j through src_v2 import scripts."
            ),
        },
        "kg_schema_summary": _schema_summary(foods, constraints),
        "query_templates": QUERY_TEMPLATES,
        "scenario_query_parameters": {
            "diseases": scenario.diseases,
            "risk_factors": scenario.risk_factors,
            "food_names": recommended_names,
            "constraint_ids": [constraint.constraint_id for constraint in active_constraints],
        },
        "retrieved_constraints": [_constraint_row(constraint) for constraint in active_constraints],
        "retrieved_food_nutrients": food_rows,
        "retrieved_guideline_provenance": [
            {
                "constraint_id": constraint.constraint_id,
                "guideline_id": constraint.guideline_id,
                "source": constraint.source,
            }
            for constraint in active_constraints
        ],
        "risk_factor_activations": [
            {
                "risk_factor": risk_factor,
                "constraint_id": constraint.constraint_id,
                "condition": constraint.condition,
            }
            for constraint in constraints
            for risk_factor in _risk_factors_for_condition(constraint.condition)
            if risk_factor in scenario.risk_factors
            and constraint.constraint_id in {
                active_constraint.constraint_id
                for active_constraint in active_constraints
            }
        ],
    }

    json_path = _resolve_path(args.output_json)
    md_path = _resolve_path(args.output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(artifact), encoding="utf-8")

    print(f"Saved KG retrieval artifact JSON to {json_path}")
    print(f"Saved KG retrieval artifact markdown to {md_path}")
    print(
        f"Scenario {scenario.scenario_id}: "
        f"{len(active_constraints)} active constraints, "
        f"{len(food_rows)} retrieved foods"
    )


def _schema_summary(
    foods: dict,
    constraints: list[NutrientConstraint],
) -> dict:
    diseases = sorted({constraint.disease for constraint in constraints})
    nutrients = sorted(
        set(_nutrient_names_from_foods(foods)) |
        {constraint.nutrient for constraint in constraints}
    )
    guidelines = sorted({constraint.guideline_id for constraint in constraints})
    risk_factors = sorted({
        risk_factor
        for constraint in constraints
        for risk_factor in _risk_factors_for_condition(constraint.condition)
    })
    risk_factor_activation_edges = sum(
        len(_risk_factors_for_condition(constraint.condition))
        for constraint in constraints
    )
    constraint_edges = len(constraints) * 3
    food_nutrient_edges = sum(
        1
        for food in foods.values()
        for value in food.nutrients.values()
        if value is not None
    )
    category_counts = Counter(food.category for food in foods.values())
    return {
        "node_counts": {
            "Food": len(foods),
            "Disease": len(diseases),
            "Nutrient": len(nutrients),
            "NutrientConstraint": len(constraints),
            "ClinicalGuideline": len(guidelines),
            "RiskFactor": len(risk_factors),
        },
        "edge_counts": {
            "Food_CONTAINS_Nutrient": food_nutrient_edges,
            "Disease_HAS_CONSTRAINT_NutrientConstraint": len(constraints),
            "NutrientConstraint_CONSTRAINT_ON_Nutrient": len(constraints),
            "NutrientConstraint_DERIVED_FROM_ClinicalGuideline": len(constraints),
            "RiskFactor_ACTIVATES_NutrientConstraint": risk_factor_activation_edges,
            "constraint_subgraph_total": constraint_edges + risk_factor_activation_edges,
        },
        "food_category_counts": dict(sorted(category_counts.items())),
    }


def _nutrient_names_from_foods(foods: dict) -> set[str]:
    names: set[str] = set()
    for food in foods.values():
        names.update(food.nutrients.keys())
    return names


def _constraint_row(constraint: NutrientConstraint) -> dict:
    return {
        "constraint_id": constraint.constraint_id,
        "disease": constraint.disease,
        "nutrient": constraint.nutrient,
        "lower_bound": constraint.lower_bound,
        "upper_bound": constraint.upper_bound,
        "unit": constraint.unit,
        "condition": constraint.condition,
        "constraint_type": constraint.constraint_type,
        "priority": constraint.priority,
        "guideline_id": constraint.guideline_id,
        "source": constraint.source,
        "note": constraint.note,
    }


def _render_markdown(artifact: dict) -> str:
    schema = artifact["kg_schema_summary"]
    params = artifact["scenario_query_parameters"]
    lines = [
        "# KG Retrieval Artifact",
        "",
        artifact["metadata"]["note"],
        "",
        "## Scenario",
        "",
        f"- Scenario: `{artifact['metadata']['scenario_id']}`",
        f"- Name: {artifact['metadata']['scenario_name']}",
        f"- Diseases: {', '.join(params['diseases'])}",
        f"- Risk factors: {', '.join(params['risk_factors']) or 'none'}",
        f"- Recommended foods: {', '.join(params['food_names'])}",
        "",
        "## Graph-Compatible Schema Counts",
        "",
        "| Node type | Count |",
        "|---|---:|",
    ]
    for name, count in schema["node_counts"].items():
        lines.append(f"| {name} | {count} |")
    lines.extend([
        "",
        "| Edge type | Count |",
        "|---|---:|",
    ])
    for name, count in schema["edge_counts"].items():
        lines.append(f"| {name} | {count} |")

    lines.extend([
        "",
        "## Retrieved Active Constraints",
        "",
        "| Constraint | Disease | Nutrient | Lower | Upper | Unit | Condition | Priority | Source |",
        "|---|---|---|---:|---:|---|---|---|---|",
    ])
    for row in artifact["retrieved_constraints"]:
        lines.append(
            "| "
            f"{row['constraint_id']} | "
            f"{row['disease']} | "
            f"{row['nutrient']} | "
            f"{_fmt_bound(row['lower_bound'])} | "
            f"{_fmt_bound(row['upper_bound'])} | "
            f"{row['unit']} | "
            f"{row['condition']} | "
            f"{row['priority']} | "
            f"{row['source']} |"
        )

    lines.extend([
        "",
        "## Risk-Factor Activations",
        "",
        "| Risk factor | Activated constraint | Condition |",
        "|---|---|---|",
    ])
    for row in artifact["risk_factor_activations"]:
        lines.append(
            f"| {row['risk_factor']} | {row['constraint_id']} | {row['condition']} |"
        )

    lines.extend([
        "",
        "## Cypher Templates",
        "",
    ])
    for name, query in artifact["query_templates"].items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append("```cypher")
        lines.append(query)
        lines.append("```")
        lines.append("")

    lines.append("## Retrieved Food Nutrients")
    lines.append("")
    lines.append("| Food | Category | Serving size (g) | Non-null nutrient fields |")
    lines.append("|---|---|---:|---:|")
    for row in artifact["retrieved_food_nutrients"]:
        non_null_count = sum(1 for value in row["nutrients"].values() if value is not None)
        lines.append(
            f"| {row['name']} | {row['category']} | "
            f"{row['serving_size_g']} | {non_null_count} |"
        )
    lines.append("")
    return "\n".join(lines)


def _find_scenario(scenarios: list[TestScenario], scenario_id: str) -> TestScenario:
    for scenario in scenarios:
        if scenario.scenario_id == scenario_id:
            return scenario
    raise ValueError(f"Scenario not found: {scenario_id}")


def _fmt_bound(value: float | None) -> str:
    if value is None:
        return ""
    return str(value)


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


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else RESULTS_DIR / path


if __name__ == "__main__":
    main()
