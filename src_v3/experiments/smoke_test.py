"""Assertions for the first executable-constraint smoke test."""

from __future__ import annotations

from ..config import DATA_DIR
from ..csv_loader import load_constraints, load_foods
from ..methods.guideline_graph_rag import evaluate_recommendation
from .metrics import conflict_detected_for
from .scenarios import load_scenarios


def main() -> None:
    foods = load_foods(DATA_DIR / "foods_extended.csv")
    constraints = load_constraints(DATA_DIR / "nutrient_constraints.csv")
    scenarios = {scenario.scenario_id: scenario for scenario in load_scenarios(DATA_DIR / "test_scenarios.csv")}

    htn_only = _evaluate(scenarios["S001"], foods, constraints)
    htn_ckd = _evaluate(scenarios["S002"], foods, constraints)
    ckd_sodium = _evaluate(scenarios["S004"], foods, constraints)
    htn_ckd_without_hyperkalemia = _evaluate(scenarios["S006"], foods, constraints)
    ckd_phosphorus = _evaluate(scenarios["S007"], foods, constraints)
    t2dm_pass = _evaluate(scenarios["S010"], foods, constraints)

    assert not htn_only["conflicts"]["has_conflict"], "HTN-only scenario should not trigger CKD potassium conflict"
    assert conflict_detected_for(htn_ckd, "potassium_mg"), "HTN+CKD scenario should detect potassium interval conflict"
    assert any(
        violation["nutrient"] == "potassium_mg" and violation["disease"] == "CKD"
        for violation in htn_ckd["verification"]["violations"]
    ), "HTN+CKD scenario should report CKD potassium upper-bound violation"
    assert any(
        violation["nutrient"] == "sodium_mg" and violation["disease"] == "CKD"
        for violation in ckd_sodium["verification"]["violations"]
    ), "CKD sodium scenario should report sodium upper-bound violation"
    assert not conflict_detected_for(
        htn_ckd_without_hyperkalemia,
        "potassium_mg",
    ), "HTN+CKD without hyperkalemia risk should not detect potassium conflict"
    assert any(
        violation["nutrient"] == "phosphorus_mg" and violation["disease"] == "CKD"
        for violation in ckd_phosphorus["verification"]["violations"]
    ), "CKD phosphorus-risk scenario should report phosphorus upper-bound violation"
    assert len([
        violation
        for violation in ckd_phosphorus["verification"]["violations"]
        if violation["nutrient"] == "phosphorus_mg" and violation["disease"] == "CKD"
    ]) == 1, "CKD phosphorus-risk scenario should report one active phosphorus violation"
    assert t2dm_pass["evidence"]["verified"], "T2DM target-range scenario should pass after conservative calibration"

    print("v2 smoke test passed")


def _evaluate(scenario, foods, constraints) -> dict:
    return evaluate_recommendation(
        recommended_foods=scenario.recommended_foods,
        food_db=foods,
        all_constraints=constraints,
        diseases=scenario.diseases,
        risk_factors=scenario.risk_factors,
        meal_type=scenario.meal_type,
    )


if __name__ == "__main__":
    main()
