"""Import graph data into Neo4j and save live KG query verification results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from neo4j.exceptions import Neo4jError, ServiceUnavailable

from ..config import DATA_DIR, RESULTS_DIR, ROOT_DIR, load_neo4j_config
from ..csv_loader import load_constraints, load_foods
from ..db import Neo4jClient
from ..models import NutrientConstraint
from .scenarios import TestScenario, load_scenarios


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-id", default="S002")
    parser.add_argument("--skip-import", action="store_true")
    parser.add_argument(
        "--foods-csv",
        default=str(ROOT_DIR / "data_usda_55" / "foods_usda_55.csv"),
        help="Food composition CSV to import. Defaults to the USDA v3 candidate table.",
    )
    parser.add_argument(
        "--constraints-csv",
        default=str(DATA_DIR / "nutrient_constraints.csv"),
        help="Guideline-derived nutrient constraints CSV.",
    )
    parser.add_argument(
        "--scenarios-csv",
        default=str(ROOT_DIR / "data_usda_55" / "test_scenarios_usda_90.csv"),
        help="Scenario CSV. Defaults to the USDA v3 90-scenario benchmark.",
    )
    parser.add_argument("--uri", default=None, help="Override NEO4J_URI, for example bolt://localhost:7687.")
    parser.add_argument("--database", default=None, help="Override NEO4J_DATABASE.")
    parser.add_argument("--output-json", default="kg_live_verification_s002.json")
    parser.add_argument("--output-md", default="kg_live_verification_s002.md")
    args = parser.parse_args()

    foods_csv = Path(args.foods_csv)
    constraints_csv = Path(args.constraints_csv)
    scenarios_csv = Path(args.scenarios_csv)

    foods = load_foods(foods_csv)
    constraints = load_constraints(constraints_csv)
    scenarios = load_scenarios(scenarios_csv)
    scenario = _find_scenario(scenarios, args.scenario_id)

    config = load_neo4j_config()
    if args.uri:
        config = config.__class__(
            uri=args.uri,
            user=config.user,
            password=config.password,
            database=args.database or config.database,
        )
    elif args.database:
        config = config.__class__(
            uri=config.uri,
            user=config.user,
            password=config.password,
            database=args.database,
        )

    try:
        with Neo4jClient(config) as db:
            connectivity = _verify_connectivity(db)
            if not args.skip_import:
                _import_foods(db, foods)
                _import_constraints(db, constraints)
            artifact = _run_queries(
                db,
                foods,
                constraints,
                scenario,
                connectivity,
                not args.skip_import,
                {
                    "foods_csv": str(foods_csv),
                    "constraints_csv": str(constraints_csv),
                    "scenarios_csv": str(scenarios_csv),
                },
            )
    except (ServiceUnavailable, Neo4jError, OSError) as error:
        artifact = _connection_failure_artifact(
            config,
            scenario,
            error,
            {
                "foods_csv": str(foods_csv),
                "constraints_csv": str(constraints_csv),
                "scenarios_csv": str(scenarios_csv),
            },
        )

    json_path = _resolve_path(args.output_json)
    md_path = _resolve_path(args.output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(artifact), encoding="utf-8")

    print(f"Saved live KG verification JSON to {json_path}")
    print(f"Saved live KG verification markdown to {md_path}")
    if artifact["metadata"].get("status") == "connection_failed":
        print("Neo4j connection failed; see artifact for details.")
        print(f"URI: {artifact['connectivity']['uri']}")
        print(f"Database: {artifact['connectivity']['database']}")
        print(f"Error: {artifact['connectivity']['error_type']}: {artifact['connectivity']['error']}")
        return
    print(
        f"Scenario {scenario.scenario_id}: "
        f"{len(artifact['queries']['active_constraints'])} active constraints, "
        f"{len(artifact['queries']['risk_factor_activations'])} risk activations, "
        f"conflict_detected={artifact['derived_checks']['potassium_interval_conflict']['has_conflict']}"
    )


def _verify_connectivity(db: Neo4jClient) -> dict[str, Any]:
    rows = db.execute("RETURN 1 AS ok")
    component_rows = db.execute(
        """
        CALL dbms.components()
        YIELD name, versions, edition
        RETURN name, versions, edition
        """
    )
    return {
        "ok": rows[0]["ok"] == 1,
        "components": component_rows,
        "database": db.config.database,
        "uri": db.config.uri,
    }


def _connection_failure_artifact(
    config: Any,
    scenario: TestScenario,
    error: BaseException,
    data_sources: dict[str, str],
) -> dict[str, Any]:
    return {
        "metadata": {
            "scenario_id": scenario.scenario_id,
            "scenario_name": scenario.name,
            "diseases": scenario.diseases,
            "risk_factors": scenario.risk_factors,
            "recommended_foods": [food.name for food in scenario.recommended_foods],
            "imported_this_run": False,
            "status": "connection_failed",
            "note": "Neo4j live verification could not connect to the configured database.",
            "data_sources": data_sources,
        },
        "connectivity": {
            "ok": False,
            "uri": config.uri,
            "database": config.database,
            "error_type": error.__class__.__name__,
            "error": str(error),
        },
        "queries": {},
        "derived_checks": {},
    }


def _import_foods(db: Neo4jClient, foods: dict) -> None:
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


def _import_constraints(db: Neo4jClient, constraints: list[NutrientConstraint]) -> None:
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
    FOREACH (risk_factor IN risk_factors |
        MERGE (r:RiskFactor {name: risk_factor})
        MERGE (r)-[:ACTIVATES]->(c)
    )
    """
    for constraint in constraints:
        db.execute(
            query,
            {
                **constraint.__dict__,
                "risk_factors": _risk_factors_for_condition(constraint.condition),
            },
        )


def _run_queries(
    db: Neo4jClient,
    foods: dict,
    constraints: list[NutrientConstraint],
    scenario: TestScenario,
    connectivity: dict[str, Any],
    imported_this_run: bool,
    data_sources: dict[str, str],
) -> dict[str, Any]:
    food_ids = [food.food_id for food in foods.values()]
    constraint_ids = [constraint.constraint_id for constraint in constraints]
    guideline_ids = sorted({constraint.guideline_id for constraint in constraints})
    nutrient_names = sorted(
        {
            nutrient
            for food in foods.values()
            for nutrient in food.nutrients
        }
        | {constraint.nutrient for constraint in constraints}
    )
    scenario_food_names = [food.name for food in scenario.recommended_foods]

    schema_counts = {
        "nodes": _single_row(
            db.execute(
                """
                MATCH (f:Food) WHERE f.food_id IN $food_ids
                WITH count(f) AS food_count
                MATCH (d:Disease) WHERE d.name IN $diseases
                WITH food_count, count(d) AS disease_count
                MATCH (n:Nutrient)
                WHERE n.name IN $nutrient_names
                WITH food_count, disease_count, count(DISTINCT n) AS nutrient_count
                MATCH (c:NutrientConstraint) WHERE c.constraint_id IN $constraint_ids
                WITH food_count, disease_count, nutrient_count, count(c) AS constraint_count
                MATCH (g:ClinicalGuideline) WHERE g.guideline_id IN $guideline_ids
                WITH food_count, disease_count, nutrient_count, constraint_count, count(g) AS guideline_count
                MATCH (r:RiskFactor)
                WHERE EXISTS {
                    MATCH (r)-[:ACTIVATES]->(c:NutrientConstraint)
                    WHERE c.constraint_id IN $constraint_ids
                }
                RETURN food_count,
                       disease_count,
                       nutrient_count,
                       constraint_count,
                       guideline_count,
                       count(DISTINCT r) AS risk_factor_count
                """,
                {
                    "food_ids": food_ids,
                    "diseases": sorted({c.disease for c in constraints}),
                    "constraint_ids": constraint_ids,
                    "guideline_ids": guideline_ids,
                    "nutrient_names": nutrient_names,
                },
            )
        ),
        "edges": _single_row(
            db.execute(
                """
                MATCH (f:Food)-[contains:CONTAINS]->(:Nutrient)
                WHERE f.food_id IN $food_ids
                  AND endNode(contains).name IN $nutrient_names
                WITH count(contains) AS food_contains_nutrient
                MATCH (:Disease)-[has_constraint:HAS_CONSTRAINT]->(c:NutrientConstraint)
                WHERE c.constraint_id IN $constraint_ids
                WITH food_contains_nutrient, count(has_constraint) AS disease_has_constraint
                MATCH (c:NutrientConstraint)-[constraint_on:CONSTRAINT_ON]->(:Nutrient)
                WHERE c.constraint_id IN $constraint_ids
                WITH food_contains_nutrient, disease_has_constraint, count(constraint_on) AS constraint_on_nutrient
                MATCH (c:NutrientConstraint)-[derived_from:DERIVED_FROM]->(:ClinicalGuideline)
                WHERE c.constraint_id IN $constraint_ids
                WITH food_contains_nutrient, disease_has_constraint, constraint_on_nutrient, count(derived_from) AS derived_from_guideline
                OPTIONAL MATCH (:RiskFactor)-[activates:ACTIVATES]->(c:NutrientConstraint)
                WHERE c.constraint_id IN $constraint_ids
                RETURN food_contains_nutrient,
                       disease_has_constraint,
                       constraint_on_nutrient,
                       derived_from_guideline,
                       count(activates) AS risk_factor_activates_constraint
                """,
                {
                    "food_ids": food_ids,
                    "constraint_ids": constraint_ids,
                    "nutrient_names": nutrient_names,
                },
            )
        ),
    }

    active_constraints = db.execute(
        """
        MATCH (d:Disease)-[:HAS_CONSTRAINT]->(c:NutrientConstraint)
              -[:CONSTRAINT_ON]->(n:Nutrient),
              (c)-[:DERIVED_FROM]->(g:ClinicalGuideline)
        WHERE d.name IN $diseases
        OPTIONAL MATCH (r:RiskFactor)-[:ACTIVATES]->(c)
        WITH d, c, n, g, collect(DISTINCT r.name) AS activating_risks
        WHERE size(activating_risks) = 0
           OR any(risk IN activating_risks WHERE risk IN $risk_factors)
        RETURN d.name AS disease,
               c.constraint_id AS constraint_id,
               n.name AS nutrient,
               c.lower_bound AS lower_bound,
               c.upper_bound AS upper_bound,
               c.unit AS unit,
               c.condition AS condition,
               c.constraint_type AS constraint_type,
               c.priority AS priority,
               g.guideline_id AS guideline_id,
               g.name AS source,
               activating_risks AS activating_risks
        ORDER BY disease, nutrient, constraint_id
        """,
        {"diseases": scenario.diseases, "risk_factors": scenario.risk_factors},
    )

    risk_factor_activations = db.execute(
        """
        MATCH (r:RiskFactor)-[:ACTIVATES]->(c:NutrientConstraint)
              <-[:HAS_CONSTRAINT]-(d:Disease)
        WHERE d.name IN $diseases AND r.name IN $risk_factors
        RETURN r.name AS risk_factor,
               d.name AS disease,
               c.constraint_id AS constraint_id,
               c.condition AS condition
        ORDER BY risk_factor, constraint_id
        """,
        {"diseases": scenario.diseases, "risk_factors": scenario.risk_factors},
    )

    food_nutrients = db.execute(
        """
        MATCH (f:Food)
        WHERE f.name IN $food_names
        OPTIONAL MATCH (f)-[r:CONTAINS]->(n:Nutrient)
        WHERE n.name IN $nutrient_names
        RETURN f.name AS food,
               f.category AS category,
               f.serving_size_g AS serving_size_g,
               count(r) AS nutrient_edge_count,
               collect({
                   nutrient: n.name,
                   amount: r.amount,
                   unit: r.unit,
                   basis: r.basis
               }) AS nutrients
        ORDER BY food
        """,
        {"food_names": scenario_food_names, "nutrient_names": nutrient_names},
    )

    provenance = db.execute(
        """
        MATCH (c:NutrientConstraint)-[:DERIVED_FROM]->(g:ClinicalGuideline)
        WHERE c.constraint_id IN $constraint_ids
        RETURN c.constraint_id AS constraint_id,
               g.guideline_id AS guideline_id,
               g.name AS source
        ORDER BY constraint_id
        """,
        {"constraint_ids": [row["constraint_id"] for row in active_constraints]},
    )

    potassium_rows = [
        row for row in active_constraints
        if row["nutrient"] == "potassium_mg"
    ]

    return {
        "metadata": {
            "scenario_id": scenario.scenario_id,
            "scenario_name": scenario.name,
            "diseases": scenario.diseases,
            "risk_factors": scenario.risk_factors,
            "recommended_foods": scenario_food_names,
            "imported_this_run": imported_this_run,
            "data_sources": data_sources,
            "note": "Live Neo4j KG verification artifact generated from configured CSV-backed graph data.",
        },
        "connectivity": connectivity,
        "queries": {
            "schema_counts": schema_counts,
            "active_constraints": active_constraints,
            "risk_factor_activations": risk_factor_activations,
            "food_nutrients": food_nutrients,
            "guideline_provenance": provenance,
        },
        "derived_checks": {
            "potassium_interval_conflict": _interval_conflict(potassium_rows),
        },
    }


def _interval_conflict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lower_values = [
        row["lower_bound"] for row in rows
        if row["lower_bound"] is not None
    ]
    upper_values = [
        row["upper_bound"] for row in rows
        if row["upper_bound"] is not None
    ]
    merged_lower = max(lower_values) if lower_values else None
    merged_upper = min(upper_values) if upper_values else None
    has_conflict = (
        merged_lower is not None
        and merged_upper is not None
        and merged_lower > merged_upper
    )
    return {
        "nutrient": "potassium_mg",
        "constraint_ids": [row["constraint_id"] for row in rows],
        "merged_lower": merged_lower,
        "merged_upper": merged_upper,
        "has_conflict": has_conflict,
    }


def _render_markdown(artifact: dict[str, Any]) -> str:
    meta = artifact["metadata"]
    if meta.get("status") == "connection_failed":
        return "\n".join([
            "# Live Neo4j KG Verification",
            "",
            artifact["metadata"]["note"],
            "",
            "## Connection Failure",
            "",
            f"- URI: `{artifact['connectivity']['uri']}`",
            f"- Database: `{artifact['connectivity']['database']}`",
            f"- Error type: `{artifact['connectivity']['error_type']}`",
            f"- Error: `{artifact['connectivity']['error']}`",
            "",
            "Start Neo4j, confirm the Bolt URI/database in `.env`, then rerun:",
            "",
            "```powershell",
            "python -m src_v3.experiments.run_kg_live_verification --scenario-id S002 --output-json kg_live_verification_s002.json --output-md kg_live_verification_s002.md",
            "```",
            "",
            "For a single-instance local Neo4j server, this override is often useful:",
            "",
            "```powershell",
            "python -m src_v3.experiments.run_kg_live_verification --uri bolt://localhost:7687 --scenario-id S002 --output-json kg_live_verification_s002.json --output-md kg_live_verification_s002.md",
            "```",
            "",
        ])
    nodes = artifact["queries"]["schema_counts"]["nodes"]
    edges = artifact["queries"]["schema_counts"]["edges"]
    conflict = artifact["derived_checks"]["potassium_interval_conflict"]
    lines = [
        "# Live Neo4j KG Verification",
        "",
        artifact["metadata"]["note"],
        "",
        "## Connection",
        "",
        f"- URI: `{artifact['connectivity']['uri']}`",
        f"- Database: `{artifact['connectivity']['database']}`",
        f"- Connectivity check: `{artifact['connectivity']['ok']}`",
        f"- Imported this run: `{meta['imported_this_run']}`",
        "",
        "## Data Sources",
        "",
        f"- Foods CSV: `{meta['data_sources']['foods_csv']}`",
        f"- Constraints CSV: `{meta['data_sources']['constraints_csv']}`",
        f"- Scenarios CSV: `{meta['data_sources']['scenarios_csv']}`",
        "",
        "## Scenario",
        "",
        f"- Scenario: `{meta['scenario_id']}`",
        f"- Name: {meta['scenario_name']}",
        f"- Diseases: {', '.join(meta['diseases'])}",
        f"- Risk factors: {', '.join(meta['risk_factors']) or 'none'}",
        f"- Recommended foods: {', '.join(meta['recommended_foods'])}",
        "",
        "## Live Schema Counts",
        "",
        "| Node count | Value |",
        "|---|---:|",
    ]
    for key, value in nodes.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "| Edge count | Value |", "|---|---:|"])
    for key, value in edges.items():
        lines.append(f"| {key} | {value} |")

    lines.extend([
        "",
        "## Active Constraints Retrieved by Cypher",
        "",
        "| Constraint | Disease | Nutrient | Lower | Upper | Unit | Condition | Priority | Source | Activating risks |",
        "|---|---|---|---:|---:|---|---|---|---|---|",
    ])
    for row in artifact["queries"]["active_constraints"]:
        lines.append(
            "| "
            f"{row['constraint_id']} | "
            f"{row['disease']} | "
            f"{row['nutrient']} | "
            f"{_fmt(row['lower_bound'])} | "
            f"{_fmt(row['upper_bound'])} | "
            f"{row['unit']} | "
            f"{row['condition']} | "
            f"{row['priority']} | "
            f"{row['source']} | "
            f"{', '.join(row['activating_risks']) or 'none'} |"
        )

    lines.extend([
        "",
        "## Risk-Factor Activations",
        "",
        "| Risk factor | Disease | Activated constraint | Condition |",
        "|---|---|---|---|",
    ])
    for row in artifact["queries"]["risk_factor_activations"]:
        lines.append(
            f"| {row['risk_factor']} | {row['disease']} | "
            f"{row['constraint_id']} | {row['condition']} |"
        )

    lines.extend([
        "",
        "## Potassium Interval Check",
        "",
        "| Nutrient | Constraints | Merged lower | Merged upper | Conflict detected |",
        "|---|---|---:|---:|---|",
        (
            f"| {conflict['nutrient']} | {', '.join(conflict['constraint_ids'])} | "
            f"{_fmt(conflict['merged_lower'])} | {_fmt(conflict['merged_upper'])} | "
            f"{conflict['has_conflict']} |"
        ),
        "",
        "## Retrieved Food Nutrient Profiles",
        "",
        "| Food | Category | Serving size (g) | Nutrient edges |",
        "|---|---|---:|---:|",
    ])
    for row in artifact["queries"]["food_nutrients"]:
        lines.append(
            f"| {row['food']} | {row['category']} | "
            f"{row['serving_size_g']} | {row['nutrient_edge_count']} |"
        )

    lines.extend([
        "",
        "## Guideline Provenance",
        "",
        "| Constraint | Guideline | Source |",
        "|---|---|---|",
    ])
    for row in artifact["queries"]["guideline_provenance"]:
        lines.append(
            f"| {row['constraint_id']} | {row['guideline_id']} | {row['source']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _find_scenario(scenarios: list[TestScenario], scenario_id: str) -> TestScenario:
    for scenario in scenarios:
        if scenario.scenario_id == scenario_id:
            return scenario
    raise ValueError(f"Scenario not found: {scenario_id}")


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


def _unit_for_nutrient(nutrient: str) -> str:
    if nutrient.endswith("_mg"):
        return "mg/serving"
    if nutrient.endswith("_g"):
        return "g/serving"
    if nutrient.endswith("_kcal"):
        return "kcal/serving"
    return "value/serving"


def _single_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    return rows[0]


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else RESULTS_DIR / path


if __name__ == "__main__":
    main()
