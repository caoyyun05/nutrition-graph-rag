"""Run constrained LLM generation baseline.

Injects KG-derived nutrient constraints into the generation prompt so the LLM
is aware of clinical bounds while generating food recommendations. The output
is then verified by the same deterministic KG verifier used for the
unconstrained baseline, enabling a direct comparison of violation rates.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ..config import DATA_DIR, RESULTS_DIR, load_llm_config
from ..csv_loader import load_constraints, load_foods, select_active_constraints
from ..llm_client import ExperimentLLMClient, LLMClientError
from ..methods import boolean_graph_rag, guideline_graph_rag, pure_kg, pure_llm
from ..models import NutrientConstraint
from ..nutrient_calculator import meal_allocation_factor
from .metrics import conflict_detected_for, summarize_guideline_result
from .scenarios import TestScenario, load_scenarios


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", help="LLM provider: kimi, openai, or anthropic.")
    parser.add_argument("--model", help="Model name.")
    parser.add_argument("--temperature", type=float, help="Sampling temperature.")
    parser.add_argument("--max-tokens", type=int, help="Maximum generated tokens.")
    parser.add_argument("--limit", type=int, help="Only run the first N scenarios.")
    parser.add_argument("--scenario-id", action="append", help="Run only selected scenario IDs.")
    parser.add_argument("--sleep-seconds", type=float, default=0.0, help="Delay between API calls.")
    parser.add_argument("--dry-run", action="store_true", help="Write prompts without calling LLM.")
    parser.add_argument(
        "--replay-raw-dir",
        help="Reuse existing raw output files instead of calling the LLM.",
    )
    parser.add_argument(
        "--output-json",
        default="constrained_llm_generation.json",
        help="Path for structured result JSON.",
    )
    parser.add_argument(
        "--raw-output-dir",
        default="constrained_llm_raw_outputs",
        help="Directory for raw LLM outputs and dry-run prompts.",
    )
    args = parser.parse_args()

    foods = load_foods(DATA_DIR / "foods_extended.csv")
    constraints = load_constraints(DATA_DIR / "nutrient_constraints.csv")
    scenarios = _select_scenarios(load_scenarios(DATA_DIR / "test_scenarios.csv"), args)
    output_path = _resolve_results_path(args.output_json)
    raw_dir = _resolve_results_path(args.raw_output_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    llm_config = load_llm_config(
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    replay_raw_dir = _resolve_results_path(args.replay_raw_dir) if args.replay_raw_dir else None
    client = None
    if not args.dry_run and replay_raw_dir is None:
        try:
            client = ExperimentLLMClient(llm_config)
        except LLMClientError as exc:
            raise SystemExit(str(exc)) from exc

    rows = []
    for index, scenario in enumerate(scenarios, start=1):
        active = select_active_constraints(constraints, scenario.diseases, scenario.risk_factors)
        prompt = _build_constrained_prompt(scenario, sorted(foods), active)
        prompt_path = raw_dir / f"{scenario.scenario_id}_prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")

        if args.dry_run:
            rows.append(_dry_run_row(scenario, prompt_path))
            continue

        raw_output_path = raw_dir / f"{scenario.scenario_id}_raw.txt"
        if replay_raw_dir is not None:
            replay_path = replay_raw_dir / f"{scenario.scenario_id}_raw.txt"
            print(f"[{index}/{len(scenarios)}] Replaying {scenario.scenario_id}")
            raw_output = replay_path.read_text(encoding="utf-8")
            if replay_path != raw_output_path:
                raw_output_path.write_text(raw_output, encoding="utf-8")
        else:
            print(f"[{index}/{len(scenarios)}] Calling LLM for {scenario.scenario_id}")
            raw_output = client.generate(prompt) if client is not None else ""
            raw_output_path.write_text(raw_output, encoding="utf-8")
        rows.append(_evaluate_llm_output(
            scenario=scenario, raw_output=raw_output,
            raw_output_path=raw_output_path, prompt_path=prompt_path,
            foods=foods, constraints=constraints,
        ))
        if replay_raw_dir is None and args.sleep_seconds > 0 and index < len(scenarios):
            time.sleep(args.sleep_seconds)

    output = {
        "metadata": {
            "runner": "run_constrained_llm_generation",
            "dry_run": args.dry_run,
            "replay_raw_dir": str(replay_raw_dir) if replay_raw_dir else None,
            "llm": _redacted_llm_metadata(llm_config),
            "food_count": len(foods),
            "constraint_count": len(constraints),
            "scenario_count": len(scenarios),
            "raw_output_dir": str(raw_dir),
            "note": (
                "Constrained generation: KG nutrient constraints are injected "
                "into the LLM prompt. Output is verified by the deterministic "
                "KG verifier for comparison with unconstrained generation."
            ),
        },
        "aggregate": _aggregate(rows),
        "scenarios": rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved constrained LLM generation results to {output_path}")
    if args.dry_run:
        print(f"Dry-run prompts saved to {raw_dir}")


def _select_scenarios(scenarios: list[TestScenario], args: argparse.Namespace) -> list[TestScenario]:
    selected = scenarios
    if args.scenario_id:
        requested = set(args.scenario_id)
        selected = [s for s in selected if s.scenario_id in requested]
    if args.limit is not None:
        selected = selected[: args.limit]
    return selected


def _format_constraint_block(
    active: list[NutrientConstraint],
    meal_type: str | None,
) -> str:
    if not active:
        return "No specific nutrient constraints apply."
    factor = meal_allocation_factor(meal_type)
    meal_label = (meal_type or "full_day").lower()
    is_meal_level = meal_label not in {"full_day", "day"}
    lines = []
    for c in active:
        bounds = []
        if c.lower_bound is not None:
            bounds.append(f">= {c.lower_bound * factor:.1f}")
        if c.upper_bound is not None:
            bounds.append(f"<= {c.upper_bound * factor:.1f}")
        bound_str = " and ".join(bounds) if bounds else "no numeric bound"
        condition_str = f" (condition: {c.condition})" if c.condition else ""
        scope = f"allocated to this {meal_type} meal" if is_meal_level else "per day"
        lines.append(
            f"- {c.nutrient}: {bound_str} {c.unit} "
            f"[{scope}; {c.disease}, {c.priority} priority]{condition_str}"
        )
    return "\n".join(lines)


def _build_constrained_prompt(
    scenario: TestScenario,
    allowed_food_names: list[str],
    active_constraints: list[NutrientConstraint],
) -> str:
    diseases = ", ".join(scenario.diseases) or "none"
    risk_factors = ", ".join(scenario.risk_factors) or "none"
    allowed_foods = ", ".join(allowed_food_names)
    constraint_block = _format_constraint_block(active_constraints, scenario.meal_type)
    return f"""Create one {scenario.meal_type} dietary recommendation for the patient scenario below.

Scenario ID: {scenario.scenario_id}
Scenario name: {scenario.name}
Diseases: {diseases}
Risk factors: {risk_factors}

IMPORTANT — Clinical nutrient constraints (from evidence-based guidelines):
{constraint_block}

You MUST ensure the total nutrients of your recommended foods stay within these
bounds for this {scenario.meal_type} recommendation. For meal-level requests,
the listed bounds have already been scaled from daily targets by the verifier's
meal allocation factor. Violating any constraint could harm the patient.

Use only foods from this allowed food list:
{allowed_foods}

Return only valid JSON in this exact schema:
{{
  "recommended_foods": [
    {{"name": "<food name copied exactly from the allowed list>", "servings": <number>}}
  ],
  "rationale": "<one short sentence explaining how the selection satisfies constraints>"
}}

Rules:
- Choose 3 to 6 foods.
- Use numeric servings such as 0.5, 1, 2, or 3.
- Do not include foods outside the allowed list.
- Do not include markdown fences or explanatory text outside the JSON.
"""


def _dry_run_row(scenario: TestScenario, prompt_path: Path) -> dict:
    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "diseases": scenario.diseases,
        "risk_factors": scenario.risk_factors,
        "meal_type": scenario.meal_type,
        "status": "dry_run",
        "prompt_path": str(prompt_path),
        "raw_output_path": None,
        "raw_output": "",
        "extraction": {
            "recommended_foods": [],
            "unmatched_items": [],
            "extraction_method": "not_run",
        },
        "methods": {},
    }


def _evaluate_llm_output(
    scenario: TestScenario,
    raw_output: str,
    raw_output_path: Path,
    prompt_path: Path,
    foods: dict,
    constraints: list,
) -> dict:
    pure_llm_result = pure_llm.evaluate_recommendation(
        recommended_foods=[],
        raw_output=raw_output,
        food_db=foods,
    )
    extracted_foods = pure_llm_result["extraction"]["recommended_foods"]
    pure_kg_result = pure_kg.evaluate_recommendation(extracted_foods, foods)
    boolean_result = boolean_graph_rag.evaluate_recommendation(
        extracted_foods, foods,
        diseases=scenario.diseases,
        risk_factors=scenario.risk_factors,
    )
    guideline_result = guideline_graph_rag.evaluate_recommendation(
        recommended_foods=extracted_foods,
        food_db=foods,
        all_constraints=constraints,
        diseases=scenario.diseases,
        risk_factors=scenario.risk_factors,
        meal_type=scenario.meal_type,
    )
    guideline_summary = summarize_guideline_result(guideline_result)

    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "diseases": scenario.diseases,
        "risk_factors": scenario.risk_factors,
        "meal_type": scenario.meal_type,
        "status": "completed",
        "prompt_path": str(prompt_path),
        "raw_output_path": str(raw_output_path),
        "raw_output": raw_output,
        "expected_conflict_nutrient": scenario.expected_conflict_nutrient,
        "expected_conflict_detected": conflict_detected_for(
            guideline_result, scenario.expected_conflict_nutrient,
        ),
        "extraction": _serialize_extraction(pure_llm_result["extraction"]),
        "methods": {
            "pure_llm": {
                "passed": pure_llm_result["passed"],
                "deterministic_verification": pure_llm_result["deterministic_verification"],
                "detected_problem": pure_llm_result["detected_problem"],
                "food_count": pure_llm_result["food_count"],
                "limitations": pure_llm_result["limitations"],
            },
            "pure_kg": {
                "passed": pure_kg_result["passed"],
                "deterministic_verification": False,
                "detected_problem": not pure_kg_result["passed"],
                "missing_food_count": len(pure_kg_result["missing_foods"]),
                "missing_nutrient_record_count": len(pure_kg_result["missing_nutrients"]),
                "limitations": pure_kg_result["limitations"],
            },
            "boolean_graph_rag": {
                "passed": boolean_result["passed"],
                "deterministic_verification": False,
                "detected_problem": not boolean_result["passed"],
                "flagged_food_count": len(boolean_result["flagged_foods"]),
                "flagged_foods": boolean_result["flagged_foods"],
                "limitations": boolean_result["limitations"],
            },
            "guideline_graph_rag": {
                "passed": guideline_summary["passed"],
                "deterministic_verification": True,
                "detected_problem": not guideline_summary["passed"],
                "violation_count": guideline_summary["violation_count"],
                "conflict_count": guideline_summary["conflict_count"],
                "missing_data_count": guideline_summary["missing_data_count"],
                "active_constraint_count": guideline_summary["active_constraint_count"],
                "violated_nutrients": sorted({
                    violation["nutrient"]
                    for violation in guideline_result["verification"].get("violations", [])
                }),
                "conflict_nutrients": sorted({
                    conflict["nutrient"]
                    for conflict in guideline_result["conflicts"].get("conflicts", [])
                }),
                "evidence_sources": guideline_result["evidence"].get("evidence_sources", []),
            },
        },
    }


def _serialize_extraction(extraction: dict) -> dict:
    return {
        "recommended_foods": [
            {"name": food.name, "servings": food.servings}
            for food in extraction["recommended_foods"]
        ],
        "unmatched_items": extraction["unmatched_items"],
        "extraction_method": extraction["extraction_method"],
    }


def _aggregate(rows: list[dict]) -> dict:
    completed = [row for row in rows if row["status"] == "completed"]
    if not completed:
        return {
            "completed_count": 0,
            "dry_run_count": sum(1 for row in rows if row["status"] == "dry_run"),
        }

    extracted_counts = [
        len(row["extraction"]["recommended_foods"]) for row in completed
    ]
    guideline_problem_count = sum(
        1 for row in completed
        if row["methods"]["guideline_graph_rag"]["detected_problem"]
    )
    boolean_problem_count = sum(
        1 for row in completed
        if row["methods"]["boolean_graph_rag"]["detected_problem"]
    )
    unmatched_count = sum(
        len(row["extraction"]["unmatched_items"]) for row in completed
    )
    conflict_scenarios = sum(
        1 for row in completed if row.get("expected_conflict_nutrient")
    )
    conflict_detected = sum(
        1 for row in completed if row.get("expected_conflict_detected")
    )
    return {
        "completed_count": len(completed),
        "dry_run_count": sum(1 for row in rows if row["status"] == "dry_run"),
        "average_extracted_food_count": round(
            sum(extracted_counts) / len(extracted_counts), 4
        ),
        "zero_extraction_count": sum(1 for c in extracted_counts if c == 0),
        "unmatched_item_count": unmatched_count,
        "guideline_problem_count": guideline_problem_count,
        "guideline_problem_rate": _ratio(guideline_problem_count, len(completed)),
        "boolean_problem_count": boolean_problem_count,
        "boolean_problem_rate": _ratio(boolean_problem_count, len(completed)),
        "conflict_scenarios": conflict_scenarios,
        "conflict_detected": conflict_detected,
        "conflict_detection_rate": _ratio(conflict_detected, conflict_scenarios),
    }


def _redacted_llm_metadata(config) -> dict:
    return {
        "provider": config.provider,
        "model": config.model,
        "base_url": config.base_url,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "api_key_present": bool(config.api_key),
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _resolve_results_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else RESULTS_DIR / path


if __name__ == "__main__":
    main()
