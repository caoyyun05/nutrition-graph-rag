"""Build the expanded v2 scenario CSV with explicit expected labels."""

from __future__ import annotations

import csv
from pathlib import Path

from ..config import DATA_DIR


FIELDNAMES = [
    "scenario_id",
    "name",
    "diseases",
    "risk_factors",
    "meal_type",
    "recommended_foods",
    "expected_passed",
    "expected_violation_nutrients",
    "expected_conflict_nutrient",
    "expected_missing_data",
    "label_source",
    "notes",
]


LABEL_SOURCE = "manual_design_v1"


def main() -> None:
    scenarios = _scenarios()
    output_path = DATA_DIR / "test_scenarios.csv"
    _write_csv(output_path, scenarios)
    print(f"Wrote {len(scenarios)} scenarios to {output_path}")


def _row(
    scenario_id: str,
    name: str,
    diseases: str,
    risk_factors: str,
    meal_type: str,
    foods: str,
    expected_passed: bool,
    expected_violation_nutrients: str = "",
    expected_conflict_nutrient: str = "",
    notes: str = "",
) -> dict[str, str]:
    return {
        "scenario_id": scenario_id,
        "name": name,
        "diseases": diseases,
        "risk_factors": risk_factors,
        "meal_type": meal_type,
        "recommended_foods": foods,
        "expected_passed": str(expected_passed).lower(),
        "expected_violation_nutrients": expected_violation_nutrients,
        "expected_conflict_nutrient": expected_conflict_nutrient,
        "expected_missing_data": "false",
        "label_source": LABEL_SOURCE,
        "notes": notes,
    }


def _scenarios() -> list[dict[str, str]]:
    rows = [
        _row("S001", "HTN only high potassium target", "HTN", "", "full_day", "Oatmeal:2;Broccoli:3;Spinach:3;Banana:2;Lentils cooked:2", True, notes="Expected to pass HTN sodium and potassium checks without triggering CKD potassium restriction."),
        _row("S002", "HTN plus CKD hyperkalemia risk", "HTN|CKD", "hyperkalemia_risk", "full_day", "Oatmeal:2;Broccoli:3;Spinach:3;Banana:2;Lentils cooked:2", False, "potassium_mg", "potassium_mg", "Expected potassium interval conflict between HTN potassium target and operational CKD hyperkalemia cap."),
        _row("S003", "T2DM low fiber and carbohydrate", "T2DM", "", "full_day", "Brown rice:2;Broccoli:2;Chicken breast:1;Apple:1;Tofu:1", False, "carbohydrate_g|fiber_g", notes="Expected T2DM fiber and carbohydrate lower-bound violations under the current adequacy targets."),
        _row("S004", "CKD sodium violation", "CKD", "hyperkalemia_risk", "full_day", "Canned soup:3;Whole wheat bread:2;Chicken breast:1", False, "sodium_mg", notes="Expected CKD sodium upper-bound violation; potassium cap is active but not necessarily violated."),
        _row("S005", "HTN high sodium and low potassium violation", "HTN", "", "full_day", "Canned soup:2;Whole wheat bread:2;Chicken breast:1", False, "potassium_mg|sodium_mg", notes="Expected HTN sodium upper-bound violations and potassium lower-bound violation."),
        _row("S006", "HTN plus CKD without hyperkalemia risk", "HTN|CKD", "", "full_day", "Oatmeal:2;Broccoli:3;Spinach:3;Banana:2;Lentils cooked:2", True, notes="Expected no potassium conflict because CKD potassium restriction is inactive without hyperkalemia-related risk."),
        _row("S007", "CKD phosphorus risk violation", "CKD", "hyperphosphatemia_risk", "full_day", "Salmon:3;Low-sodium yogurt:2;Brown rice:1", False, "phosphorus_mg", notes="Expected strict phosphorus upper-bound violation when hyperphosphatemia risk is active."),
        _row("S008", "T2DM low fiber and carbohydrate test", "T2DM", "", "full_day", "Low-sodium yogurt:5;Apple:1;White rice:1", False, "carbohydrate_g|fiber_g", notes="Expected T2DM fiber and carbohydrate lower-bound violations."),
        _row("S009", "HTN dinner sodium allocation violation", "HTN", "", "dinner", "Canned soup:1;Whole wheat bread:1", False, "potassium_mg|sodium_mg", notes="Expected meal-level sodium violations after dinner allocation factor and potassium lower-bound violation."),
        _row("S010", "T2DM target-range pass", "T2DM", "", "full_day", "Brown rice:3;Lentils cooked:3;Broccoli:2;Chicken breast:1", True, notes="Expected to satisfy current T2DM sodium fiber carbohydrate and added-sugar constraints."),
        _row("S011", "HTN alternative potassium pass", "HTN", "", "full_day", "Oatmeal:2;Kale:3;Potato baked:2;Orange:2;Black beans cooked:2", True, notes="Expected to pass HTN sodium and potassium targets using the expanded food table."),
        _row("S012", "HTN low potassium pattern", "HTN", "", "full_day", "White rice:2;Chicken breast:2;Cucumber:2", False, "potassium_mg", notes="Expected HTN potassium lower-bound violation with otherwise low sodium foods."),
        _row("S013", "HTN processed dinner violation", "HTN", "", "dinner", "Ham:1;Salted crackers:1", False, "potassium_mg|sodium_mg", notes="Expected dinner-level sodium violations and potassium lower-bound violation."),
        _row("S014", "CKD hyperkalemia potassium violation", "CKD", "hyperkalemia_risk", "full_day", "Potato baked:2;Orange juice:2;Spinach:2", False, "potassium_mg", notes="Expected CKD potassium upper-bound violation without HTN potassium conflict."),
        _row("S015", "CKD hyperkalemia potassium pass", "CKD", "hyperkalemia_risk", "full_day", "White rice:2;Chicken breast:1;Cucumber:2", True, notes="Expected to pass CKD sodium and operational potassium cap."),
        _row("S016", "CKD elevated phosphorus soft violation", "CKD", "elevated_serum_phosphorus", "full_day", "Cheddar cheese:3;Milk low-fat:2;Shrimp:1", False, "phosphorus_mg", notes="Expected soft phosphorus upper-bound violation when elevated_serum_phosphorus is specified."),
        _row("S017", "CKD phosphorus risk pass", "CKD", "hyperphosphatemia_risk", "full_day", "White rice:2;Apple:1;Cucumber:2", True, notes="Expected to pass strict phosphorus and sodium checks."),
        _row("S018", "T2DM borderline low carbohydrate", "T2DM", "", "full_day", "Quinoa cooked:2;Black beans cooked:2;Broccoli:2;Egg:1", False, "carbohydrate_g", notes="Expected carbohydrate lower-bound violation while fiber and sodium pass."),
        _row("S019", "T2DM added sugar violation", "T2DM", "", "full_day", "Soda:2;Cookies:2;White rice:1", False, "added_sugar_g|fiber_g", notes="Expected added-sugar upper-bound violation and low-fiber violation."),
        _row("S020", "T2DM processed sodium violation", "T2DM", "", "full_day", "Instant noodles:1;Ham:1;Canned soup:1", False, "carbohydrate_g|fiber_g|sodium_mg", notes="Expected sodium upper-bound violation plus low fiber and low carbohydrate."),
        _row("S021", "HTN plus CKD potassium compatible", "HTN|CKD", "", "full_day", "Oatmeal:2;Potato baked:2;Kale:3;Black beans cooked:2", True, notes="Expected to pass because CKD potassium cap is inactive without hyperkalemia risk."),
        _row("S022", "HTN plus CKD second potassium conflict", "HTN|CKD", "hyperkalemia_risk", "full_day", "Potato baked:2;Banana:2;Spinach:2;Black beans cooked:2", False, "potassium_mg", "potassium_mg", "Expected second potassium interval conflict case using expanded high-potassium foods."),
        _row("S023", "T2DM plus HTN sodium potassium fiber violation", "T2DM|HTN", "", "full_day", "Canned soup:2;Whole wheat bread:2;Soda:1", False, "fiber_g|potassium_mg|sodium_mg", notes="Expected HTN/T2DM sodium violations plus HTN low-potassium and T2DM low-fiber violations."),
        _row("S024", "T2DM plus CKD low fiber carbohydrate", "T2DM|CKD", "hyperkalemia_risk", "full_day", "Instant noodles:1;Low-sodium yogurt:2;Apple:1", False, "carbohydrate_g|fiber_g", notes="Expected T2DM fiber and carbohydrate lower-bound violations; CKD sodium and potassium remain within current caps."),
        _row("S025", "T2DM plus CKD compatible pattern", "T2DM|CKD", "", "full_day", "Quinoa cooked:2;Broccoli:2;Chicken breast:1;Apple:2;Lentils cooked:1", True, notes="Expected to pass current T2DM and CKD sodium checks without hyperkalemia-risk potassium cap."),
        _row("S026", "HTN breakfast sodium allocation violation", "HTN", "", "breakfast", "Bagel:1;Ham:1", False, "potassium_mg|sodium_mg", notes="Expected breakfast sodium allocation violations and potassium lower-bound violation."),
        _row("S027", "T2DM lunch low fiber carbohydrate", "T2DM", "", "lunch", "White rice:1;Chicken breast:1", False, "carbohydrate_g|fiber_g", notes="Expected lunch-level fiber and carbohydrate lower-bound violations after allocation scaling."),
        _row("S028", "CKD sodium pass", "CKD", "", "full_day", "White rice:2;Tofu:1;Apple:1;Cucumber:2", True, notes="Expected to pass CKD sodium check with no electrolyte risk factors active."),
        _row("S029", "T2DM HTN CKD potassium conflict", "T2DM|HTN|CKD", "hyperkalemia_risk", "full_day", "Potato baked:2;Spinach:2;Black beans cooked:2;Soda:1", False, "potassium_mg", "potassium_mg", "Expected all-comorbidity potassium conflict with CKD potassium violation."),
        _row("S030", "T2DM HTN CKD processed high sodium conflict", "T2DM|HTN|CKD", "hyperkalemia_risk", "full_day", "Instant noodles:1;Ham:1;Canned soup:1;Cookies:1", False, "carbohydrate_g|fiber_g|potassium_mg|sodium_mg", "potassium_mg", "Expected all-comorbidity potassium interval conflict plus sodium and T2DM adequacy violations."),
    ]

    rows.extend(_additional_scenarios())
    return rows


def _additional_scenarios() -> list[dict[str, str]]:
    return [
        _row("S031", "HTN DASH-like full-day pass", "HTN", "", "full_day", "Oatmeal:2;Spinach:2;Banana:2;Potato baked:1;Black beans cooked:2", True, notes="High-potassium low-sodium HTN pattern."),
        _row("S032", "HTN low potassium lean-protein fail", "HTN", "", "full_day", "White rice:2;Turkey breast:2;Cucumber:2;Apple:1", False, "potassium_mg", notes="Low-potassium HTN pattern."),
        _row("S033", "HTN sodium processed lunch fail", "HTN", "", "lunch", "Instant noodles:1;Ham:1", False, "potassium_mg|sodium_mg", notes="Meal-level sodium and potassium failure."),
        _row("S034", "HTN potassium upper excess", "HTN", "", "full_day", "Potato baked:4;Spinach:3;Banana:3;Black beans cooked:2", False, "potassium_mg", notes="Exceeds HTN operational potassium upper bound."),
        _row("S035", "HTN breakfast low potassium", "HTN", "", "breakfast", "Oatmeal:1;Apple:1;Egg:1", False, "potassium_mg", notes="Breakfast allocation potassium lower-bound failure."),
        _row("S036", "HTN low sodium but insufficient potassium", "HTN", "", "full_day", "Brown rice:2;Chicken breast:2;Broccoli:2;Apple:1", False, "potassium_mg", notes="Low sodium alone is insufficient for HTN potassium target."),
        _row("S037", "HTN processed snack sodium fail", "HTN", "", "snack", "Salted crackers:1;Potato chips:1", False, "potassium_mg|sodium_mg", notes="Snack allocation high sodium and low potassium."),
        _row("S038", "HTN high potassium upper violation", "HTN", "", "full_day", "Oatmeal:2;Kale:2;Sweet potato baked:2;Banana:2;Lentils cooked:2", False, "potassium_mg", notes="Exceeds the current HTN operational potassium upper bound."),
        _row("S039", "HTN potassium violation with moderate sodium", "HTN", "", "full_day", "Whole wheat bread:4;Turkey breast:2;Broccoli:2;Banana:2;Potato baked:1", False, "potassium_mg", notes="Potassium remains outside the current HTN target range; sodium does not exceed active threshold."),
        _row("S040", "T2DM high fiber carbohydrate pass", "T2DM", "", "full_day", "Brown rice:3;Black beans cooked:3;Broccoli:2;Apple:1;Oatmeal:1", True, notes="T2DM adequacy pass with high fiber."),
        _row("S041", "T2DM low carbohydrate protein-heavy fail", "T2DM", "", "full_day", "Chicken breast:2;Egg:2;Salmon:1;Broccoli:1", False, "carbohydrate_g|fiber_g", notes="Protein-heavy pattern below carbohydrate and fiber floors."),
        _row("S042", "T2DM sugary beverage fail", "T2DM", "", "full_day", "Soda:2;White rice:2;Chicken breast:1;Cookies:1", False, "added_sugar_g|fiber_g", notes="Added sugar and fiber failure."),
        _row("S043", "T2DM high sodium processed fail", "T2DM", "", "full_day", "Instant noodles:1;Pepperoni pizza:1;Sugary cereal:1", False, "carbohydrate_g|fiber_g|sodium_mg", notes="High sodium with low fiber and carbohydrate adequacy failure."),
        _row("S044", "T2DM lunch adequate pass", "T2DM", "", "lunch", "Brown rice:1;Lentils cooked:1;Broccoli:1;Apple:1", True, notes="Lunch allocation pass for T2DM adequacy."),
        _row("S045", "T2DM breakfast low fiber fail", "T2DM", "", "breakfast", "Bagel:1;Egg:1", False, "fiber_g", notes="Breakfast fiber lower-bound failure."),
        _row("S046", "T2DM dinner carbohydrate low fail", "T2DM", "", "dinner", "Salmon:1;Broccoli:1;Spinach:1;Tofu:1", False, "carbohydrate_g|fiber_g", notes="Dinner low carbohydrate and fiber."),
        _row("S047", "T2DM added sugar boundary pass", "T2DM", "", "full_day", "Brown rice:3;Black beans cooked:2;Broccoli:2;Soda:1", True, notes="Added sugar remains below operational upper bound while adequacy targets pass."),
        _row("S048", "T2DM high GI low fiber fail", "T2DM", "", "full_day", "White rice:2;Bagel:1;Chicken breast:1", False, "fiber_g", notes="GI is not currently constrained; fiber failure remains active."),
        _row("S049", "T2DM fiber pass carbohydrate low fail", "T2DM", "", "full_day", "Broccoli:4;Black beans cooked:2;Almonds:1", False, "carbohydrate_g", notes="Fiber passes but carbohydrate adequacy fails."),
        _row("S050", "CKD sodium simple pass", "CKD", "", "full_day", "White rice:2;Apple:1;Cucumber:2;Tofu:1", True, notes="CKD sodium pass without electrolyte risk factors."),
        _row("S051", "CKD sodium processed fail", "CKD", "", "full_day", "Canned soup:2;Ham:1;Whole wheat bread:1", False, "sodium_mg", notes="CKD sodium upper-bound failure."),
        _row("S052", "CKD hyperkalemia high potassium fail", "CKD", "hyperkalemia_risk", "full_day", "Potato baked:2;Banana:2;Spinach:1", False, "potassium_mg", notes="CKD potassium cap failure."),
        _row("S053", "CKD hyperkalemia controlled pass", "CKD", "hyperkalemia_risk", "full_day", "White rice:2;Chicken breast:1;Cucumber:2;Apple:1", True, notes="CKD sodium and potassium pass."),
        _row("S054", "CKD phosphorus strict fail dairy fish", "CKD", "hyperphosphatemia_risk", "full_day", "Salmon:2;Low-sodium yogurt:2;Brown rice:1", False, "phosphorus_mg", notes="Strict phosphorus upper-bound failure."),
        _row("S055", "CKD phosphorus strict pass rice fruit", "CKD", "hyperphosphatemia_risk", "full_day", "White rice:2;Apple:1;Cucumber:2;Tofu:1", True, notes="Strict phosphorus pass."),
        _row("S056", "CKD elevated phosphorus soft fail cheese", "CKD", "elevated_serum_phosphorus", "full_day", "Cheddar cheese:4;Milk low-fat:2;Chicken breast:1", False, "phosphorus_mg", notes="Soft phosphorus target failure."),
        _row("S057", "CKD elevated phosphorus soft pass", "CKD", "elevated_serum_phosphorus", "full_day", "White rice:2;Apple:1;Cucumber:2;Chicken breast:1", True, notes="Soft phosphorus pass."),
        _row("S058", "CKD lunch sodium allocation fail", "CKD", "", "lunch", "Canned soup:1;Whole wheat bread:1", False, "sodium_mg", notes="Meal-level CKD sodium failure."),
        _row("S059", "CKD hyperkalemia lunch pass", "CKD", "hyperkalemia_risk", "lunch", "White rice:1;Chicken breast:1;Cucumber:1", True, notes="Meal-level CKD potassium pass."),
        _row("S060", "CKD hyperkalemia lunch fail", "CKD", "hyperkalemia_risk", "lunch", "Potato baked:1;Spinach:1", False, "potassium_mg", notes="Meal-level CKD potassium cap failure."),
        _row("S061", "HTN CKD compatible high potassium no risk pass", "HTN|CKD", "", "full_day", "Oatmeal:2;Potato baked:2;Kale:2;Black beans cooked:2", True, notes="CKD potassium cap inactive, HTN potassium target passes."),
        _row("S062", "HTN CKD hyperkalemia conflict high potassium", "HTN|CKD", "hyperkalemia_risk", "full_day", "Oatmeal:2;Potato baked:2;Kale:2;Black beans cooked:2", False, "potassium_mg", "potassium_mg", "Expected potassium interval conflict."),
        _row("S063", "HTN CKD hyperkalemia low potassium conflict", "HTN|CKD", "hyperkalemia_risk", "full_day", "White rice:2;Chicken breast:1;Cucumber:2", False, "potassium_mg", "potassium_mg", "Expected conflict even when actual intake is below HTN target."),
        _row("S064", "HTN CKD sodium fail no hyperkalemia", "HTN|CKD", "", "full_day", "Canned soup:2;Whole wheat bread:2;Chicken breast:1", False, "potassium_mg|sodium_mg", notes="Sodium failure and low potassium without CKD potassium conflict."),
        _row("S065", "HTN CKD breakfast sodium fail", "HTN|CKD", "", "breakfast", "Bagel:1;Ham:1", False, "potassium_mg|sodium_mg", notes="Meal-level sodium and potassium failure."),
        _row("S066", "HTN CKD hyperkalemia sodium plus conflict", "HTN|CKD", "hyperkalemia_risk", "full_day", "Canned soup:2;Potato baked:2;Spinach:1", False, "potassium_mg|sodium_mg", "potassium_mg", "Sodium violation plus potassium conflict."),
        _row("S067", "T2DM HTN potassium upper fail", "T2DM|HTN", "", "full_day", "Oatmeal:2;Brown rice:3;Black beans cooked:3;Broccoli:2;Banana:2", False, "potassium_mg", notes="T2DM adequacy passes but HTN potassium exceeds the current operational upper bound."),
        _row("S068", "T2DM HTN low fiber potassium fail", "T2DM|HTN", "", "full_day", "White rice:2;Chicken breast:2;Apple:1", False, "carbohydrate_g|fiber_g|potassium_mg", notes="Multiple lower-bound failures."),
        _row("S069", "T2DM HTN processed sodium fail", "T2DM|HTN", "", "full_day", "Instant noodles:1;Canned soup:1;Whole wheat bread:1", False, "carbohydrate_g|fiber_g|potassium_mg|sodium_mg", notes="Processed high-sodium T2DM plus HTN failure."),
        _row("S070", "T2DM HTN sugary low potassium fail", "T2DM|HTN", "", "full_day", "Soda:2;Cookies:2;White rice:1", False, "added_sugar_g|fiber_g|potassium_mg", notes="Added sugar, fiber, and potassium failure."),
        _row("S071", "T2DM HTN lunch potassium fail", "T2DM|HTN", "", "lunch", "Brown rice:1;Lentils cooked:1;Broccoli:1;Banana:1", False, "potassium_mg", notes="Meal-level T2DM targets pass but HTN potassium exceeds allocated upper bound."),
        _row("S072", "T2DM CKD compatible pass no hyperkalemia", "T2DM|CKD", "", "full_day", "Brown rice:3;Lentils cooked:3;Broccoli:2;Chicken breast:1", True, notes="T2DM pass and CKD sodium pass."),
        _row("S073", "T2DM CKD hyperkalemia potassium fail", "T2DM|CKD", "hyperkalemia_risk", "full_day", "Brown rice:3;Lentils cooked:3;Broccoli:2;Potato baked:1", False, "potassium_mg", notes="CKD potassium cap failure with T2DM adequacy pass."),
        _row("S074", "T2DM CKD low fiber carbohydrate fail", "T2DM|CKD", "hyperkalemia_risk", "full_day", "White rice:2;Chicken breast:1;Cucumber:2", False, "carbohydrate_g|fiber_g", notes="T2DM adequacy failure with CKD potassium pass."),
        _row("S075", "T2DM CKD sodium fail", "T2DM|CKD", "", "full_day", "Canned soup:2;Instant noodles:1;Apple:1", False, "carbohydrate_g|fiber_g|sodium_mg", notes="CKD/T2DM sodium failure plus fiber and carbohydrate adequacy failure."),
        _row("S076", "T2DM CKD phosphorus and fiber risk fail", "T2DM|CKD", "hyperphosphatemia_risk", "full_day", "Brown rice:3;Salmon:2;Low-sodium yogurt:2;Broccoli:1", False, "fiber_g|phosphorus_mg", notes="CKD phosphorus failure with T2DM fiber adequacy failure."),
        _row("S077", "T2DM CKD phosphorus risk pass", "T2DM|CKD", "hyperphosphatemia_risk", "full_day", "Brown rice:3;Black beans cooked:3;Broccoli:2;Apple:1", True, notes="T2DM adequacy and CKD phosphorus pass."),
        _row("S078", "Triple no hyperkalemia potassium upper fail", "T2DM|HTN|CKD", "", "full_day", "Oatmeal:2;Brown rice:3;Black beans cooked:3;Broccoli:2;Banana:2", False, "potassium_mg", notes="CKD potassium cap is inactive, but HTN potassium upper bound is exceeded."),
        _row("S079", "Triple hyperkalemia conflict high potassium", "T2DM|HTN|CKD", "hyperkalemia_risk", "full_day", "Oatmeal:2;Brown rice:3;Black beans cooked:3;Broccoli:2;Banana:2", False, "potassium_mg", "potassium_mg", "Expected potassium conflict and CKD potassium violation."),
        _row("S080", "Triple processed sodium conflict", "T2DM|HTN|CKD", "hyperkalemia_risk", "full_day", "Instant noodles:1;Ham:1;Canned soup:1;Cookies:1", False, "carbohydrate_g|fiber_g|potassium_mg|sodium_mg", "potassium_mg", "Expected potassium conflict plus sodium and T2DM adequacy violations."),
        _row("S081", "Triple low potassium adequacy fail conflict", "T2DM|HTN|CKD", "hyperkalemia_risk", "full_day", "White rice:2;Chicken breast:1;Cucumber:2;Apple:1", False, "carbohydrate_g|fiber_g|potassium_mg", "potassium_mg", "Expected conflict with actual low potassium intake."),
        _row("S082", "Triple phosphorus and potassium risks", "T2DM|HTN|CKD", "hyperkalemia_risk|hyperphosphatemia_risk", "full_day", "Salmon:3;Low-sodium yogurt:2;Potato baked:1;Brown rice:2", False, "fiber_g|phosphorus_mg|potassium_mg", "potassium_mg", "Expected potassium conflict plus phosphorus and fiber violations."),
        _row("S083", "Triple lunch conflict", "T2DM|HTN|CKD", "hyperkalemia_risk", "lunch", "Potato baked:1;Spinach:1;Brown rice:1;Broccoli:1", False, "potassium_mg", "potassium_mg", "Meal-level potassium conflict case."),
        _row("S084", "Triple breakfast sodium and conflict", "T2DM|HTN|CKD", "hyperkalemia_risk", "breakfast", "Bagel:1;Ham:1;Banana:1", False, "fiber_g|potassium_mg|sodium_mg", "potassium_mg", "Breakfast sodium and potassium conflict."),
        _row("S085", "CKD elevated phosphorus low sodium pass", "CKD", "elevated_serum_phosphorus", "full_day", "White rice:2;Apple:1;Cucumber:2;Tofu:1", True, notes="Elevated phosphorus soft target pass."),
        _row("S086", "T2DM snack sugar sodium fail", "T2DM", "", "snack", "Soda:1;Cookies:1", False, "added_sugar_g|fiber_g|sodium_mg", notes="Snack allocation added sugar, sodium, and fiber failure."),
        _row("S087", "HTN snack potassium upper fail", "HTN", "", "snack", "Banana:1;Almonds:1", False, "potassium_mg", notes="Snack potassium exceeds allocated HTN upper bound."),
        _row("S088", "CKD snack phosphorus sodium fail", "CKD", "hyperphosphatemia_risk", "snack", "Cheddar cheese:1;Low-sodium yogurt:1", False, "phosphorus_mg|sodium_mg", notes="Snack phosphorus and sodium allocation failure."),
        _row("S089", "T2DM HTN CKD no risk low sodium but low fiber", "T2DM|HTN|CKD", "", "full_day", "Brown rice:2;Chicken breast:2;Broccoli:1;Apple:1", False, "carbohydrate_g|fiber_g|potassium_mg", notes="No conflict but multiple adequacy failures."),
        _row("S090", "Triple no risk potassium upper fail", "T2DM|HTN|CKD", "", "full_day", "Oatmeal:2;Brown rice:3;Black beans cooked:3;Broccoli:3;Potato baked:1", False, "potassium_mg", notes="No CKD potassium cap, but HTN potassium upper bound is exceeded."),
    ]


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
