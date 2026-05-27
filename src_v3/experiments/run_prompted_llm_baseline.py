"""Run the Guideline-Prompted LLM verification baseline.

This script sends each scenario's constraints and food recommendations to the
LLM, asking it to judge violations. Results are saved for replay and comparison.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import DATA_DIR, RESULTS_DIR, load_llm_config
from ..csv_loader import load_constraints, load_foods, select_active_constraints
from ..llm_client import ExperimentLLMClient, LLMClientError
from ..methods import prompted_llm_verifier
from .scenarios import load_scenarios


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", default="prompted_llm_baseline.json")
    parser.add_argument("--replay", default=None, help="Path to saved outputs for replay.")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    foods = load_foods(DATA_DIR / "foods_extended.csv")
    constraints = load_constraints(DATA_DIR / "nutrient_constraints.csv")
    scenarios = load_scenarios(DATA_DIR / "test_scenarios.csv")

    saved_outputs: dict[str, str] | None = None
    if args.replay:
        replay_path = Path(args.replay)
        if replay_path.exists():
            saved_outputs = json.loads(replay_path.read_text(encoding="utf-8"))

    client = None
    if saved_outputs is None:
        try:
            config = load_llm_config(provider=args.provider, model=args.model)
            client = ExperimentLLMClient(config)
        except LLMClientError as e:
            print(f"LLM client unavailable: {e}")
            print("Run with --replay to use saved outputs.")
            return

    results = []
    raw_outputs: dict[str, str] = {}

    for scenario in scenarios:
        active = select_active_constraints(
            constraints, scenario.diseases, scenario.risk_factors,
        )
        prompt = prompted_llm_verifier.build_verification_prompt(
            scenario.recommended_foods, foods, active, scenario.meal_type,
        )

        if saved_outputs is not None:
            llm_output = saved_outputs.get(scenario.scenario_id, "")
        elif client is not None:
            llm_output = client.generate(prompt)
            raw_outputs[scenario.scenario_id] = llm_output
        else:
            llm_output = ""

        result = prompted_llm_verifier.evaluate_recommendation(
            recommended_foods=scenario.recommended_foods,
            food_db=foods,
            all_constraints=constraints,
            diseases=scenario.diseases,
            risk_factors=scenario.risk_factors,
            meal_type=scenario.meal_type,
            llm_output=llm_output if llm_output else None,
        )

        results.append({
            "scenario_id": scenario.scenario_id,
            "name": scenario.name,
            "diseases": scenario.diseases,
            "passed": result["passed"],
            "detected_problem": result["detected_problem"],
            "violated_nutrients": result.get("violated_nutrients", []),
            "conflict_nutrients": result.get("conflict_nutrients", []),
            "judgment": result.get("judgment"),
        })

    output_path = _resolve_output_path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "metadata": {
            "method": "prompted_llm_verifier",
            "scenario_count": len(scenarios),
            "replay": args.replay is not None,
        },
        "results": results,
    }
    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    if raw_outputs:
        raw_path = output_path.with_name("prompted_llm_raw_outputs.json")
        raw_path.write_text(
            json.dumps(raw_outputs, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        print(f"Saved raw LLM outputs to {raw_path}")

    _print_summary(results)
    print(f"\nSaved results to {output_path}")


def _resolve_output_path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else RESULTS_DIR / p


def _print_summary(results: list[dict]) -> None:
    total = len(results)
    detected = sum(1 for r in results if r["detected_problem"])
    passed = sum(1 for r in results if r["passed"] is True)
    failed = sum(1 for r in results if r["passed"] is False)
    unknown = sum(1 for r in results if r["passed"] is None)

    print(f"Prompted LLM Verifier Baseline")
    print(f"  Scenarios: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed (problems detected): {failed}")
    print(f"  Unknown (no output): {unknown}")
    print(f"  Problem detection rate: {detected}/{total} = {detected/total:.4f}")

    conflict_scenarios = [r for r in results if r["conflict_nutrients"]]
    print(f"  Conflict detections: {len(conflict_scenarios)}")


if __name__ == "__main__":
    main()