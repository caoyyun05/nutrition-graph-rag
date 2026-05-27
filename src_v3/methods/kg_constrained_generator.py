"""End-to-end KG-constrained LLM generation pipeline.

Demonstrates the full architecture:
  Neo4j KG → retrieve constraints → inject into LLM prompt → generate → verify
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..config import load_llm_config, load_neo4j_config
from ..csv_loader import load_constraints, load_foods, select_active_constraints
from ..db import Neo4jClient
from ..interval_verifier import verify_nutrient_ranges
from ..conflict_detector import detect_interval_conflicts
from ..evidence_report import build_evidence_report
from ..kg_repository import ClinicalKGRepository
from ..llm_client import ExperimentLLMClient, LLMClientError
from ..llm_food_extractor import extract_recommended_foods
from ..models import NutrientConstraint, RecommendedFood
from ..nutrient_calculator import compute_nutrient_totals


@dataclass
class PipelineResult:
    kg_constraints: list[dict]
    active_constraints: list[NutrientConstraint]
    prompt: str
    llm_raw_output: str
    extracted_foods: list[RecommendedFood]
    unmatched_items: list[str]
    nutrient_totals: dict[str, float]
    verification: dict
    conflicts: dict
    evidence: dict
    passed: bool


def query_constraints_from_neo4j(
    diseases: list[str],
) -> list[dict]:
    """Query nutrient constraints directly from Neo4j KG."""
    config = load_neo4j_config()
    with Neo4jClient(config) as client:
        repo = ClinicalKGRepository(client)
        return repo.get_nutrient_constraints(diseases)


def neo4j_rows_to_constraints(rows: list[dict]) -> list[NutrientConstraint]:
    """Convert Neo4j query results to NutrientConstraint objects."""
    return [
        NutrientConstraint(
            constraint_id=row["constraint_id"],
            disease=row["disease"],
            nutrient=row["nutrient"],
            lower_bound=row.get("lower_bound"),
            upper_bound=row.get("upper_bound"),
            unit=row.get("unit", ""),
            condition=row.get("condition", ""),
            constraint_type=row.get("constraint_type", ""),
            priority=row.get("priority", ""),
            guideline_id=row.get("guideline_id", ""),
            source=row.get("source", ""),
            note=row.get("note", ""),
        )
        for row in rows
    ]


def format_constraints_for_prompt(
    constraints: list[NutrientConstraint],
    risk_factors: list[str] | None = None,
) -> str:
    """Format active constraints into a human-readable block for LLM prompt."""
    active = select_active_constraints(constraints,
        [c.disease for c in constraints], risk_factors)
    if not active:
        return "No specific nutrient constraints apply."
    lines = []
    for c in active:
        bounds = []
        if c.lower_bound is not None:
            bounds.append(f">= {c.lower_bound}")
        if c.upper_bound is not None:
            bounds.append(f"<= {c.upper_bound}")
        bound_str = " and ".join(bounds) if bounds else "no numeric bound"
        condition_str = f" (condition: {c.condition})" if c.condition else ""
        lines.append(
            f"- {c.nutrient}: {bound_str} {c.unit} "
            f"[{c.disease}, {c.priority} priority]{condition_str}"
        )
    return "\n".join(lines)


def build_kg_constrained_prompt(
    diseases: list[str],
    risk_factors: list[str],
    meal_type: str,
    allowed_food_names: list[str],
    constraints: list[NutrientConstraint],
) -> str:
    """Build a generation prompt with KG-retrieved constraints."""
    active = select_active_constraints(constraints, diseases, risk_factors)
    lines = []
    for c in active:
        bounds = []
        if c.lower_bound is not None:
            bounds.append(f">= {c.lower_bound}")
        if c.upper_bound is not None:
            bounds.append(f"<= {c.upper_bound}")
        bound_str = " and ".join(bounds) if bounds else "no numeric bound"
        cond = f" (condition: {c.condition})" if c.condition else ""
        lines.append(f"- {c.nutrient}: {bound_str} {c.unit} [{c.disease}, {c.priority}]{cond}")
    constraint_block = "\n".join(lines) if lines else "No specific nutrient constraints."
    diseases_str = ", ".join(diseases) or "none"
    risk_str = ", ".join(risk_factors) or "none"
    foods_str = ", ".join(sorted(allowed_food_names))
    return f"""Create one {meal_type} dietary recommendation for the patient below.

Diseases: {diseases_str}
Risk factors: {risk_str}

IMPORTANT — Clinical nutrient constraints (retrieved from Knowledge Graph):
{constraint_block}

You MUST ensure the total nutrients stay within these bounds for a single {meal_type} meal.

Use only foods from this allowed food list:
{foods_str}

Return only valid JSON:
{{
  "recommended_foods": [
    {{"name": "<food name from allowed list>", "servings": <number>}}
  ],
  "rationale": "<one short sentence>"
}}

Rules:
- Choose 3 to 6 foods.
- Use numeric servings such as 0.5, 1, 2, or 3.
- Do not include foods outside the allowed list.
- Do not include markdown fences or explanatory text outside the JSON.
"""


def run_full_pipeline(
    diseases: list[str],
    risk_factors: list[str],
    meal_type: str,
    food_db: dict,
    use_neo4j: bool = True,
    csv_constraints: list[NutrientConstraint] | None = None,
) -> PipelineResult:
    """Run the full KG → LLM → Verify pipeline.

    If use_neo4j=True, constraints are queried from Neo4j.
    Otherwise, csv_constraints must be provided (for offline testing).
    """
    if use_neo4j:
        kg_rows = query_constraints_from_neo4j(diseases)
        constraints = neo4j_rows_to_constraints(kg_rows)
    else:
        kg_rows = []
        constraints = csv_constraints or []

    active = select_active_constraints(constraints, diseases, risk_factors)
    prompt = build_kg_constrained_prompt(
        diseases, risk_factors, meal_type, list(food_db.keys()), constraints
    )

    llm_config = load_llm_config()
    client = ExperimentLLMClient(llm_config)
    raw_output = client.generate(prompt)

    extraction = extract_recommended_foods(raw_output, food_db)
    extracted_foods = extraction["recommended_foods"]
    unmatched = extraction["unmatched_items"]

    nutrient_totals = compute_nutrient_totals(extracted_foods, food_db)
    verification = verify_nutrient_ranges(nutrient_totals, active, meal_type=meal_type)
    conflicts = detect_interval_conflicts(active)
    evidence = build_evidence_report(verification, conflicts)

    passed = (
        len(verification.get("violations", [])) == 0
        and not conflicts.get("has_conflict", False)
    )

    return PipelineResult(
        kg_constraints=kg_rows,
        active_constraints=active,
        prompt=prompt,
        llm_raw_output=raw_output,
        extracted_foods=extracted_foods,
        unmatched_items=unmatched,
        nutrient_totals=nutrient_totals,
        verification=verification,
        conflicts=conflicts,
        evidence=evidence,
        passed=passed,
    )
