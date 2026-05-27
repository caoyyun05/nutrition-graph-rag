"""Streamlit dashboard for the USDA v3 nutrition verification workflow."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src_v3.config import DATA_DIR, RESULTS_DIR, ROOT_DIR
from src_v3.csv_loader import load_constraints, load_foods, select_active_constraints
from src_v3.experiments.metrics import conflict_detected_for, summarize_guideline_result
from src_v3.experiments.run_real_llm_baseline import _build_prompt
from src_v3.experiments.scenarios import TestScenario, load_scenarios
from src_v3.llm_food_extractor import extract_recommended_foods
from src_v3.methods import boolean_graph_rag, guideline_graph_rag, pure_kg, pure_llm
from src_v3.models import RecommendedFood


USDA_DATA_DIR = ROOT_DIR / "data_usda_55"
USDA_RESULTS_DIR = ROOT_DIR / "results_usda_55"
USDA_FOODS = USDA_DATA_DIR / "foods_usda_55.csv"
USDA_MAPPING = USDA_DATA_DIR / "food_source_mapping_usda_55.csv"
USDA_SCENARIOS = USDA_DATA_DIR / "test_scenarios_usda_90.csv"
CONSTRAINTS = DATA_DIR / "nutrient_constraints.csv"
GUIDELINES = DATA_DIR / "clinical_guidelines.csv"
MULTI_LLM_DIR = RESULTS_DIR / "multi_llm_audit_usda_pilot"
MULTI_LLM_METRICS_MD = RESULTS_DIR / "multi_llm_audit_usda_pilot_metrics.md"
MULTI_LLM_INTERPRETATION_MD = RESULTS_DIR / "multi_llm_audit_usda_pilot_interpretation.md"


st.set_page_config(page_title="Nutrition KG-RAG Verifier", layout="wide")


@st.cache_data(show_spinner=False)
def _load_usda_bundle() -> tuple[dict, list, list[TestScenario]]:
    foods = load_foods(USDA_FOODS)
    constraints = load_constraints(CONSTRAINTS)
    scenarios = load_scenarios(USDA_SCENARIOS)
    return foods, constraints, scenarios


@st.cache_data(show_spinner=False)
def _read_csv(path: str) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


@st.cache_data(show_spinner=False)
def _read_json(path: str) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _read_text(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")


def _scenario_label(scenario: TestScenario) -> str:
    return f"{scenario.scenario_id} | {scenario.name}"


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


def _page_brief(shows: str, sources: list[Path | str], proves: str) -> None:
    source_text = "\n".join(f"- `{source}`" for source in sources)
    st.info(
        f"**This page shows:** {shows}\n\n"
        f"**Data source:**\n{source_text}\n\n"
        f"**What it supports in the paper:** {proves}"
    )


def _label(text: str, tone: str = "blue") -> None:
    colors = {
        "blue": ("#EBF8FF", "#2B6CB0"),
        "green": ("#F0FFF4", "#2F855A"),
        "amber": ("#FFFAF0", "#B7791F"),
        "gray": ("#F7FAFC", "#4A5568"),
        "red": ("#FFF5F5", "#C53030"),
    }
    background, foreground = colors.get(tone, colors["blue"])
    st.markdown(
        f"<span style='background:{background}; color:{foreground}; "
        "border:1px solid currentColor; border-radius:4px; "
        "padding:2px 6px; font-size:0.82rem; font-weight:600;'>"
        f"{text}</span>",
        unsafe_allow_html=True,
    )


def _run_module(module: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )


def _render_process_result(process: subprocess.CompletedProcess[str]) -> bool:
    if process.returncode == 0:
        st.success("Command completed successfully.")
        if process.stdout.strip():
            st.code(process.stdout.strip(), language="text")
        return True
    st.error(f"Command failed with exit code {process.returncode}.")
    if process.stdout.strip():
        st.code(process.stdout.strip(), language="text")
    if process.stderr.strip():
        st.code(process.stderr.strip(), language="text")
    return False


def _evaluate_foods(
    recommended_foods: list[RecommendedFood],
    diseases: list[str],
    risk_factors: list[str],
    meal_type: str,
    foods: dict,
    constraints: list,
) -> dict:
    pure_llm_result = pure_llm.evaluate_recommendation(recommended_foods)
    pure_kg_result = pure_kg.evaluate_recommendation(recommended_foods, foods)
    boolean_result = boolean_graph_rag.evaluate_recommendation(
        recommended_foods,
        foods,
        diseases=diseases,
        risk_factors=risk_factors,
    )
    guideline_result = guideline_graph_rag.evaluate_recommendation(
        recommended_foods=recommended_foods,
        food_db=foods,
        all_constraints=constraints,
        diseases=diseases,
        risk_factors=risk_factors,
        meal_type=meal_type,
    )
    return {
        "pure_llm": pure_llm_result,
        "pure_kg": pure_kg_result,
        "boolean_graph_rag": boolean_result,
        "guideline_graph_rag": guideline_result,
    }


def _guideline_summary(result: dict) -> dict:
    summary = summarize_guideline_result(result)
    return {
        "verified": summary["passed"],
        "violations": summary["violation_count"],
        "hard violations": summary.get("hard_violation_count", 0),
        "soft misses": summary.get("soft_target_miss_count", 0),
        "conflicts": summary["conflict_count"],
        "missing data": summary["missing_data_count"],
        "active constraints": summary["active_constraint_count"],
    }


def _render_guideline_result(result: dict) -> None:
    summary = _guideline_summary(result)
    cols = st.columns(7)
    for col, (label, value) in zip(cols, summary.items()):
        col.metric(label, "Yes" if value is True else "No" if value is False else value)

    if summary["verified"]:
        st.success("No verifier findings for the currently encoded constraints.")
    else:
        st.warning("Verifier findings detected. Review violations, conflicts, and evidence.")

    tabs = st.tabs(["Nutrient totals", "Violations", "Conflicts", "Active constraints", "Evidence", "Raw JSON"])
    with tabs[0]:
        rows = [
            {"nutrient": nutrient, "value": round(value, 2)}
            for nutrient, value in sorted(result["nutrient_totals"].items())
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    with tabs[1]:
        violations = result["verification"].get("violations", [])
        if violations:
            st.dataframe(violations, use_container_width=True, hide_index=True)
        else:
            st.success("No nutrient-range violations.")
    with tabs[2]:
        conflicts = result["conflicts"].get("conflicts", [])
        if conflicts:
            for conflict in conflicts:
                st.warning(
                    f"{conflict['nutrient']}: merged lower {conflict['merged_lower']} "
                    f"> merged upper {conflict['merged_upper']}"
                )
                st.dataframe(conflict["constraints"], use_container_width=True, hide_index=True)
        else:
            st.success("No interval conflicts.")
    with tabs[3]:
        st.dataframe(result.get("active_constraint_details", []), use_container_width=True, hide_index=True)
    with tabs[4]:
        sources = result["evidence"].get("evidence_sources", [])
        if sources:
            for source in sources:
                st.write(f"- {source}")
        else:
            st.info("No triggered evidence sources because no finding was reported.")
    with tabs[5]:
        st.code(json.dumps(result, ensure_ascii=False, indent=2), language="json")


def _page_overview() -> None:
    foods, constraints, scenarios = _load_usda_bundle()
    st.header("System Overview")
    st.caption("A reproducibility dashboard for the current USDA v3 nutrition KG-RAG verifier.")

    st.subheader("Two Experimental Flows")
    flow1, flow2 = st.columns(2)
    with flow1:
        st.markdown("**Flow 1: Verifier Validation**")
        _label("Deterministic local experiment", "green")
        st.write(
            "Uses structured test scenarios with known expected outcomes to check whether "
            "the verifier detects guideline violations and comorbidity conflicts better than baselines."
        )
        st.markdown(
            "- Input: USDA 55-food table, guideline constraints, 90 scenarios\n"
            "- Output: pass/finding labels, nutrient totals, conflicts, evidence\n"
            "- No LLM API calls"
        )
    with flow2:
        st.markdown("**Flow 2: Multi-LLM Audit**")
        _label("Saved real LLM outputs; live API optional", "amber")
        st.write(
            "Uses disease-only prompts sent to Kimi and DeepSeek, then verifies whether "
            "their recommended foods satisfy executable nutrition constraints."
        )
        st.markdown(
            "- Input: disease/risk profile and allowed food names\n"
            "- Output: extracted foods, verifier findings, model comparison metrics\n"
            "- Live API calls require explicit confirmation"
        )

    st.subheader("Current Package Status")
    cols = st.columns(5)
    cols[0].metric("Foods", len(foods))
    cols[1].metric("Scenarios", len(scenarios))
    cols[2].metric("Constraints", len(constraints))
    cols[3].metric("LLM models", 2)
    cols[4].metric("Saved LLM calls", 60)

    st.subheader("What Is Real Data vs. Illustration")
    st.dataframe(
        [
            {
                "dashboard area": "Data & Knowledge Base",
                "content type": "Real local CSV data",
                "purpose": "Inspect food composition, source mapping, and guideline constraints.",
            },
            {
                "dashboard area": "Knowledge Graph Schema",
                "content type": "Illustrative schema",
                "purpose": "Explain node and edge types used by the KG-compatible verifier.",
            },
            {
                "dashboard area": "CSV-backed KG View",
                "content type": "Generated from real CSV data",
                "purpose": "Show graph-equivalent counts and disease-centered constraints.",
            },
            {
                "dashboard area": "S002 Subgraph",
                "content type": "Representative fixed visualization plus real active constraints",
                "purpose": "Explain the HTN-CKD potassium conflict used as a key example.",
            },
            {
                "dashboard area": "Live Neo4j Check",
                "content type": "Optional real database query",
                "purpose": "Confirm that the graph-database implementation can reproduce a representative verification.",
            },
            {
                "dashboard area": "Multi-LLM Audit",
                "content type": "Saved real API outputs",
                "purpose": "Inspect Kimi and DeepSeek recommendations and deterministic verifier findings.",
            },
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Suggested Reading Order")
    st.markdown(
        "1. Data & Knowledge Base\n"
        "2. Knowledge Graph Explorer\n"
        "3. Verifier Validation\n"
        "4. Multi-LLM Audit\n"
        "5. Reproducibility"
    )


def _page_data_knowledge() -> None:
    foods, constraints, scenarios = _load_usda_bundle()
    st.header("Data & Knowledge Base")
    st.caption("USDA candidate food composition data and executable guideline constraints.")
    _page_brief(
        "the local data tables used by the verifier before any experiment is run.",
        [USDA_FOODS, USDA_MAPPING, CONSTRAINTS, GUIDELINES, USDA_SCENARIOS],
        "documents that food composition and guideline constraints come from explicit, inspectable records.",
    )

    food_rows = _read_csv(str(USDA_FOODS))
    mapping_rows = _read_csv(str(USDA_MAPPING))
    guideline_rows = _read_csv(str(GUIDELINES))
    constraint_rows = _read_csv(str(CONSTRAINTS))

    cols = st.columns(5)
    cols[0].metric("Foods", len(foods))
    cols[1].metric("Nutrients per food", 10)
    cols[2].metric("Constraints", len(constraints))
    cols[3].metric("Guidelines", len(guideline_rows))
    cols[4].metric("Scenarios", len(scenarios))

    st.subheader("Food Composition Table")
    st.caption("USDA FoodData Central-mapped candidate food records used by the verifier.")
    category_options = sorted({row.get("category", "") for row in food_rows})
    selected_categories = st.multiselect("Food categories", category_options, default=category_options)
    visible_foods = [row for row in food_rows if row.get("category", "") in selected_categories]
    st.dataframe(visible_foods, use_container_width=True, hide_index=True)

    with st.expander("Food source mapping and caveats", expanded=False):
        st.dataframe(mapping_rows, use_container_width=True, hide_index=True)
        note = _read_text(str(USDA_DATA_DIR / "MANUSCRIPT_DATA_SOURCE_NOTE.md"))
        if note:
            st.markdown(note)

    st.subheader("Guideline-Derived Constraints")
    c1, c2, c3 = st.columns(3)
    diseases = sorted({row.get("disease", "") for row in constraint_rows})
    nutrients = sorted({row.get("nutrient", "") for row in constraint_rows})
    types = sorted({row.get("constraint_type", "") for row in constraint_rows})
    selected_diseases = c1.multiselect("Disease", diseases, default=diseases)
    selected_nutrients = c2.multiselect("Nutrient", nutrients, default=nutrients)
    selected_types = c3.multiselect("Constraint type", types, default=types)
    visible_constraints = [
        row
        for row in constraint_rows
        if row.get("disease", "") in selected_diseases
        and row.get("nutrient", "") in selected_nutrients
        and row.get("constraint_type", "") in selected_types
    ]
    st.dataframe(visible_constraints, use_container_width=True, hide_index=True)

    with st.expander("Clinical guideline source records", expanded=False):
        st.dataframe(guideline_rows, use_container_width=True, hide_index=True)


def _kg_edges(foods: dict, constraints: list) -> dict[str, int]:
    nutrient_names = set()
    for food in foods.values():
        nutrient_names.update(food.nutrients.keys())
    return {
        "Food nodes": len(foods),
        "Disease nodes": len({constraint.disease for constraint in constraints}),
        "Nutrient nodes": len(nutrient_names),
        "NutrientConstraint nodes": len(constraints),
        "Food-CONTAINS-Nutrient edges": len(foods) * len(nutrient_names),
        "Disease-HAS_CONSTRAINT edges": len(constraints),
        "Constraint-CONSTRAINT_ON-Nutrient edges": len(constraints),
        "Constraint-DERIVED_FROM-Guideline edges": len(constraints),
    }


def _page_kg_explorer() -> None:
    foods, constraints, scenarios = _load_usda_bundle()
    st.header("Knowledge Graph Explorer")
    st.caption("Schema explanation, CSV-backed graph-equivalent view, and optional Neo4j verification.")
    _page_brief(
        "how the verifier represents foods, nutrients, diseases, constraints, and guideline evidence as a graph-compatible structure.",
        [USDA_FOODS, CONSTRAINTS, GUIDELINES, USDA_SCENARIOS],
        "clarifies that the main experiments use an executable KG-compatible representation, with Neo4j available as implementation validation.",
    )

    st.subheader("1. KG Schema View")
    _label("Illustrative schema", "gray")
    st.caption("This diagram explains node and edge types. It is not a live database rendering.")
    st.graphviz_chart(
        """
        digraph {
          rankdir=LR;
          node [shape=box, style="rounded,filled", fillcolor="#F7FAFC", color="#4A5568"];
          Food -> Nutrient [label="CONTAINS"];
          Disease -> NutrientConstraint [label="HAS_CONSTRAINT"];
          NutrientConstraint -> Nutrient [label="CONSTRAINT_ON"];
          NutrientConstraint -> ClinicalGuideline [label="DERIVED_FROM"];
          RiskFactor -> NutrientConstraint [label="ACTIVATES"];
        }
        """
    )

    st.subheader("2. CSV-Backed Graph View")
    _label("Generated from real CSV data", "green")
    st.caption("These counts are computed from the loaded food and constraint files.")
    counts = _kg_edges(foods, constraints)
    st.dataframe([{"element": key, "count": value} for key, value in counts.items()], hide_index=True)

    st.subheader("Disease-Centered Constraint View")
    _label("Real guideline constraint records", "green")
    disease = st.selectbox("Disease", sorted({constraint.disease for constraint in constraints}))
    active = [constraint for constraint in constraints if constraint.disease == disease]
    st.dataframe([constraint.__dict__ for constraint in active], use_container_width=True, hide_index=True)

    st.subheader("3. Representative Subgraph: S002 Potassium Conflict")
    _label("Fixed explanatory graph plus real active constraints", "amber")
    st.caption(
        "The diagram is a compact explanation of the key S002 conflict. "
        "The table below it is generated from the actual active constraints for S002."
    )
    s002 = next(s for s in scenarios if s.scenario_id == "S002")
    active_s002 = select_active_constraints(constraints, s002.diseases, s002.risk_factors)
    st.graphviz_chart(
        """
        digraph {
          rankdir=LR;
          node [shape=box, style="rounded,filled", fillcolor="#FFFFFF"];
          HTN -> C_HTN_K_001 [label="HAS_CONSTRAINT"];
          CKD -> C_CKD_K_001 [label="HAS_CONSTRAINT"];
          hyperkalemia_risk -> C_CKD_K_001 [label="ACTIVATES"];
          C_HTN_K_001 -> potassium_mg [label=">= 3500 mg/day"];
          C_CKD_K_001 -> potassium_mg [label="<= 2000 mg/day"];
          C_HTN_K_001 -> ACC_AHA [label="DERIVED_FROM"];
          C_CKD_K_001 -> KDOQI_KDIGO [label="DERIVED_FROM"];
        }
        """
    )
    st.dataframe([constraint.__dict__ for constraint in active_s002], use_container_width=True, hide_index=True)

    with st.expander("4. Advanced: run live Neo4j S002 verification"):
        _label("Optional real database query", "blue")
        st.caption("Requires a running Neo4j database configured in `.env`.")
        if st.button("Run live Neo4j verification", type="secondary"):
            process = _run_module(
                "src_v3.experiments.run_kg_live_verification",
                [
                    "--scenario-id",
                    "S002",
                    "--foods-csv",
                    str(USDA_FOODS),
                    "--constraints-csv",
                    str(CONSTRAINTS),
                    "--scenarios-csv",
                    str(USDA_SCENARIOS),
                    "--output-json",
                    "streamlit_kg_live_verification_s002.json",
                    "--output-md",
                    "streamlit_kg_live_verification_s002.md",
                ],
            )
            if _render_process_result(process):
                text = _read_text(str(RESULTS_DIR / "streamlit_kg_live_verification_s002.md"))
                if text:
                    st.markdown(text)


def _page_verifier_validation() -> None:
    foods, constraints, scenarios = _load_usda_bundle()
    st.header("Verifier Validation")
    st.caption("Structured USDA 90-scenario benchmark for validating the deterministic verifier.")
    _page_brief(
        "one selected test scenario, its deterministic verifier result, and the saved 90-scenario baseline comparison.",
        [USDA_FOODS, CONSTRAINTS, USDA_SCENARIOS, USDA_RESULTS_DIR / "baseline_comparison_usda_90.json"],
        "shows that guideline-aware verification detects more clinically relevant findings than weaker baselines.",
    )

    _label("Deterministic local computation", "green")
    scenario = st.selectbox("Scenario", scenarios, format_func=_scenario_label)
    st.write(f"**Diseases:** {_format_list(scenario.diseases)}")
    st.write(f"**Risk factors:** {_format_list(scenario.risk_factors)}")
    st.write(f"**Meal type:** {scenario.meal_type}")
    st.write(f"**Expected passed:** {scenario.expected_passed}")
    if scenario.expected_conflict_nutrient:
        st.write(f"**Expected conflict:** `{scenario.expected_conflict_nutrient}`")
    st.caption(scenario.notes)

    st.subheader("Scenario Recommendation")
    st.dataframe(
        [{"name": food.name, "servings": food.servings} for food in scenario.recommended_foods],
        use_container_width=True,
        hide_index=True,
    )

    results = _evaluate_foods(
        scenario.recommended_foods,
        scenario.diseases,
        scenario.risk_factors,
        scenario.meal_type,
        foods,
        constraints,
    )
    guideline = results["guideline_graph_rag"]
    if scenario.expected_conflict_nutrient:
        st.info(
            f"Expected conflict `{scenario.expected_conflict_nutrient}` detected: "
            f"{conflict_detected_for(guideline, scenario.expected_conflict_nutrient)}"
        )
    _render_guideline_result(guideline)

    st.subheader("Saved 90-Scenario Baseline Comparison")
    _label("Saved experiment result", "blue")
    baseline = _read_json(str(USDA_RESULTS_DIR / "baseline_comparison_usda_90.json"))
    if baseline:
        totals = baseline["aggregate"]["method_totals"]
        rows = []
        for method, values in totals.items():
            rows.append(
                {
                    "method": method,
                    "passed": values["passed_count"],
                    "flagged findings": values["problem_detected_count"],
                    "flagged rate": values["problem_detection_rate"],
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.warning("USDA baseline result file not found.")

    with st.expander("Advanced: re-run USDA 90-scenario validation and baseline comparison"):
        _label("Local re-run; no LLM API", "amber")
        st.caption("Runs local deterministic scripts against USDA v3 data. No LLM API calls.")
        if st.button("Run deterministic USDA benchmark", type="secondary"):
            commands = [
                (
                    "Validate labels",
                    "src_v3.experiments.validate_scenario_labels",
                    [
                        "--foods-csv",
                        str(USDA_FOODS),
                        "--constraints-csv",
                        str(CONSTRAINTS),
                        "--scenarios-csv",
                        str(USDA_SCENARIOS),
                        "--output-json",
                        str(USDA_RESULTS_DIR / "streamlit_scenario_label_validation_usda_90.json"),
                        "--fail-on-mismatch",
                    ],
                ),
                (
                    "Run baseline comparison",
                    "src_v3.experiments.run_baseline_comparison",
                    [
                        "--foods-csv",
                        str(USDA_FOODS),
                        "--constraints-csv",
                        str(CONSTRAINTS),
                        "--scenarios-csv",
                        str(USDA_SCENARIOS),
                        "--output-json",
                        str(USDA_RESULTS_DIR / "streamlit_baseline_comparison_usda_90.json"),
                    ],
                ),
            ]
            for label, module, args in commands:
                st.write(f"**{label}**")
                process = _run_module(module, args)
                if not _render_process_result(process):
                    break


def _load_multi_llm_runs() -> list[dict[str, Any]]:
    if not MULTI_LLM_DIR.exists():
        return []
    rows = []
    for path in sorted(MULTI_LLM_DIR.glob("*.json")):
        if path.name == "manifest.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        llm = data.get("metadata", {}).get("llm", {})
        for scenario in data.get("scenarios", []):
            if scenario.get("status") != "completed":
                continue
            guideline = scenario["methods"]["guideline_graph_rag"]
            rows.append(
                {
                    "run": path.stem,
                    "provider": llm.get("provider", ""),
                    "model": llm.get("model", ""),
                    "scenario_id": scenario["scenario_id"],
                    "raw_output": scenario.get("raw_output", ""),
                    "extraction": scenario.get("extraction", {}),
                    "guideline": guideline,
                    "scenario": scenario,
                }
            )
    return rows


def _page_multi_llm_audit() -> None:
    foods, constraints, scenarios = _load_usda_bundle()
    st.header("Multi-LLM Audit")
    st.caption("Disease-only prompts sent to Kimi and DeepSeek, followed by deterministic verification.")
    _page_brief(
        "saved Kimi and DeepSeek recommendations, prompt design, extraction results, and verifier findings.",
        [USDA_SCENARIOS, MULTI_LLM_DIR, MULTI_LLM_METRICS_MD, MULTI_LLM_INTERPRETATION_MD],
        "supports the claim that plausible LLM recommendations can still miss executable nutrition constraints and require verification.",
    )

    metrics = _read_text(str(MULTI_LLM_METRICS_MD))
    if metrics:
        with st.expander("Saved 60-output pilot metrics", expanded=True):
            _label("Saved real API outputs", "blue")
            st.markdown(metrics)
    interpretation = _read_text(str(MULTI_LLM_INTERPRETATION_MD))
    if interpretation:
        with st.expander("Pilot interpretation", expanded=False):
            st.markdown(interpretation)

    st.subheader("Prompt Preview")
    _label("Disease-only prompt; no numeric nutrient thresholds", "green")
    scenario = st.selectbox("Scenario for prompt", scenarios, format_func=_scenario_label, key="llm_scenario")
    prompt = _build_prompt(scenario, sorted(foods))
    st.code(prompt, language="text")
    st.info("The prompt provides disease/risk information and the allowed food list only. It does not provide nutrient thresholds or food nutrient values.")

    st.subheader("Saved Output Comparison")
    _label("Saved real LLM outputs replayed locally", "blue")
    runs = _load_multi_llm_runs()
    if not runs:
        st.warning("No saved multi-LLM pilot outputs found.")
    else:
        scenario_ids = sorted({row["scenario_id"] for row in runs})
        selected_id = st.selectbox("Saved scenario", scenario_ids)
        selected_rows = [row for row in runs if row["scenario_id"] == selected_id]
        summary_rows = []
        for row in selected_rows:
            g = row["guideline"]
            foods_text = "; ".join(
                f"{item['name']}:{item['servings']}"
                for item in row["extraction"].get("recommended_foods", [])
            )
            summary_rows.append(
                {
                    "run": row["run"],
                    "provider": row["provider"],
                    "foods": foods_text,
                    "any finding": g.get("detected_problem"),
                    "hard safety issue": g.get("has_hard_safety_issue"),
                    "soft target miss": g.get("has_soft_target_miss"),
                    "violated nutrients": ", ".join(g.get("violated_nutrients", [])),
                    "conflict nutrients": ", ".join(g.get("conflict_nutrients", [])),
                }
            )
        st.dataframe(summary_rows, use_container_width=True, hide_index=True)

        selected_run = st.selectbox("Inspect raw output", selected_rows, format_func=lambda r: r["run"])
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Raw LLM output**")
            st.code(selected_run["raw_output"], language="json")
        with cols[1]:
            st.markdown("**Extracted foods**")
            st.dataframe(
                selected_run["extraction"].get("recommended_foods", []),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown("**Guideline verifier summary**")
            st.json(selected_run["guideline"], expanded=False)

    st.subheader("Advanced Run Controls")
    st.caption("Default use is saved-result inspection. Live API calls are optional and require confirmation.")
    mode = st.radio("Mode", ["Dry-run prompts only", "Replay saved pilot metrics", "Live API mini-run"], horizontal=True)
    if mode == "Dry-run prompts only":
        if st.button("Generate dry-run prompts", type="secondary"):
            process = _run_module(
                "src_v3.experiments.run_multi_llm_audit",
                [
                    "--model",
                    "kimi:moonshot-v1-8k",
                    "--model",
                    "deepseek:deepseek-chat",
                    "--repeats",
                    "2",
                    "--limit",
                    "3",
                    "--dry-run",
                    "--output-dir",
                    "streamlit_multi_llm_audit_usda_dryrun",
                ],
            )
            _render_process_result(process)
    elif mode == "Replay saved pilot metrics":
        if st.button("Regenerate pilot metrics", type="secondary"):
            process = _run_module(
                "src_v3.experiments.generate_multi_llm_audit_metrics",
                [
                    "--input-dir",
                    "multi_llm_audit_usda_pilot",
                    "--output-json",
                    "streamlit_multi_llm_audit_usda_pilot_metrics.json",
                    "--output-md",
                    "streamlit_multi_llm_audit_usda_pilot_metrics.md",
                ],
            )
            if _render_process_result(process):
                text = _read_text(str(RESULTS_DIR / "streamlit_multi_llm_audit_usda_pilot_metrics.md"))
                if text:
                    st.markdown(text)
    else:
        st.warning("This calls external LLM APIs. Keep the limit small for manual checks.")
        confirmed = st.checkbox("I understand this will call Kimi and DeepSeek APIs and may incur cost.")
        limit = st.number_input("Scenario limit", min_value=1, max_value=10, value=3, step=1)
        repeats = st.number_input("Repeats", min_value=1, max_value=3, value=1, step=1)
        if st.button("Run live API mini-run", disabled=not confirmed):
            process = _run_module(
                "src_v3.experiments.run_multi_llm_audit",
                [
                    "--model",
                    "kimi:moonshot-v1-8k",
                    "--model",
                    "deepseek:deepseek-chat",
                    "--repeats",
                    str(repeats),
                    "--limit",
                    str(limit),
                    "--output-dir",
                    "streamlit_multi_llm_audit_usda_live",
                ],
            )
            _render_process_result(process)


def _page_reproducibility() -> None:
    st.header("Reproducibility & Manuscript Results")
    st.caption("Result files and commands corresponding to the current v3 manuscript tables.")
    _page_brief(
        "the file-to-table crosswalk and command lines needed to reproduce saved results.",
        [USDA_RESULTS_DIR, RESULTS_DIR, ROOT_DIR / "paper_submission"],
        "helps readers trace manuscript claims back to concrete data and result artifacts.",
    )

    files = [
        ("Table 6 baseline comparison", USDA_RESULTS_DIR / "baseline_comparison_usda_90.json"),
        ("Table 7 multi-LLM metrics", MULTI_LLM_METRICS_MD),
        ("Table 8 multi-LLM interpretation", MULTI_LLM_INTERPRETATION_MD),
        ("Table 9 ablation", USDA_RESULTS_DIR / "ablation_study_usda_90.md"),
        ("Scenario label validation", USDA_RESULTS_DIR / "scenario_label_validation_usda_90.json"),
        ("USDA deterministic audit summary", USDA_RESULTS_DIR / "USDA_55_DETERMINISTIC_AUDIT_SUMMARY.md"),
    ]
    rows = []
    for label, path in files:
        rows.append(
            {
                "artifact": label,
                "path": str(path),
                "exists": path.exists(),
                "last modified": path.stat().st_mtime if path.exists() else None,
                "size": path.stat().st_size if path.exists() else None,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Core Commands")
    st.code(
        "\n".join(
            [
                "python -m src_v3.experiments.validate_scenario_labels --foods-csv data_usda_55/foods_usda_55.csv --constraints-csv data_v2/nutrient_constraints.csv --scenarios-csv data_usda_55/test_scenarios_usda_90.csv --output-json results_usda_55/scenario_label_validation_usda_90.json --fail-on-mismatch",
                "python -m src_v3.experiments.run_baseline_comparison --foods-csv data_usda_55/foods_usda_55.csv --constraints-csv data_v2/nutrient_constraints.csv --scenarios-csv data_usda_55/test_scenarios_usda_90.csv --output-json results_usda_55/baseline_comparison_usda_90.json",
                "python -m src_v3.experiments.run_ablation_study --foods-csv data_usda_55/foods_usda_55.csv --constraints-csv data_v2/nutrient_constraints.csv --scenarios-csv data_usda_55/test_scenarios_usda_90.csv --output-json results_usda_55/ablation_study_usda_90.json --output-md results_usda_55/ablation_study_usda_90.md",
                "python -m src_v3.experiments.run_multi_llm_audit --model kimi:moonshot-v1-8k --model deepseek:deepseek-chat --repeats 3 --limit 10 --output-dir multi_llm_audit_usda_pilot",
                "python -m src_v3.experiments.generate_multi_llm_audit_metrics --input-dir multi_llm_audit_usda_pilot --output-json multi_llm_audit_usda_pilot_metrics.json --output-md multi_llm_audit_usda_pilot_metrics.md",
            ]
        ),
        language="powershell",
    )

    st.subheader("Manuscript Crosswalk")
    st.dataframe(
        [
            {"manuscript item": "Table 6", "source": "results_usda_55/baseline_comparison_usda_90.json"},
            {"manuscript item": "Table 7", "source": "results_v2/multi_llm_audit_usda_pilot_metrics.md/json"},
            {"manuscript item": "Table 8", "source": "results_v2/multi_llm_audit_usda_pilot_metrics.md"},
            {"manuscript item": "Table 9", "source": "results_usda_55/ablation_study_usda_90.md/json"},
            {"manuscript item": "Figure 6", "source": "src_v3/experiments/generate_figure6_multillm_pipeline.py"},
        ],
        use_container_width=True,
        hide_index=True,
    )


def main() -> None:
    st.title("Nutrition KG-RAG Verification Dashboard")
    st.caption("USDA v3 data, deterministic verifier validation, and multi-LLM recommendation audit.")

    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Page",
            [
                "System Overview",
                "Data & Knowledge Base",
                "Knowledge Graph Explorer",
                "Verifier Validation",
                "Multi-LLM Audit",
                "Reproducibility",
            ],
        )
        st.divider()
        st.caption("Active package")
        st.caption(f"`{ROOT_DIR}`")
        st.caption("Default dataset: `data_usda_55`")
        st.caption("API calls: disabled unless explicitly selected in Multi-LLM Audit")

    if page == "System Overview":
        _page_overview()
    elif page == "Data & Knowledge Base":
        _page_data_knowledge()
    elif page == "Knowledge Graph Explorer":
        _page_kg_explorer()
    elif page == "Verifier Validation":
        _page_verifier_validation()
    elif page == "Multi-LLM Audit":
        _page_multi_llm_audit()
    else:
        _page_reproducibility()


if __name__ == "__main__":
    main()
