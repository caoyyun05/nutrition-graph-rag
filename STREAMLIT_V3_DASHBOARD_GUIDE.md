# Streamlit V3 Dashboard Guide

Use project root:

```powershell
cd D:\claude\study\paper\nutrition-graph-rag-github-ready
```

Start Streamlit yourself:

```powershell
streamlit run src_v3\streamlit_app.py
```

The dashboard now defaults to the USDA v3 candidate data path.

## Page 1: System Overview

Purpose: understand the complete dashboard before inspecting individual experiments.

This page separates the system into two flows:

- Flow 1: deterministic verifier validation.
- Flow 2: multi-LLM audit using saved Kimi and DeepSeek outputs.

It also explains what is real data, what is generated from CSV files, what is an illustrative schema, and what requires optional live Neo4j verification.

Recommended first check:

- Confirm the active package path points to `nutrition-graph-rag-github-ready`.
- Confirm the dashboard reports 55 foods, 90 scenarios, and 60 saved LLM calls.

## Page 2: Data & Knowledge Base

Purpose: inspect the data used by the verifier.

What to check:

- `data_usda_55/foods_usda_55.csv`
- `data_usda_55/food_source_mapping_usda_55.csv`
- `data_v2/nutrient_constraints.csv`
- `data_v2/clinical_guidelines.csv`

Use this page to understand:

- which 55 foods are included,
- which USDA FDC source records map to each food,
- which nutrient fields are available,
- which guideline-derived constraints are hard or soft,
- which guideline source each constraint uses.

Important caveat:

- GI is a proxy field.
- Added sugar is unavailable for many USDA entries and may be imputed.

## Page 3: Knowledge Graph Explorer

Purpose: understand the KG-compatible schema and the S002 conflict graph.

This page has four sections:

- KG Schema View: illustrative schema, not live database rendering.
- CSV-Backed Graph View: graph-equivalent counts generated from real CSV data.
- Disease-Centered Constraint View: real guideline constraint records.
- Representative Subgraph S002: fixed explanatory diagram plus real active constraints.

Recommended check:

- Open the S002 potassium conflict subgraph.
- Confirm HTN potassium target and CKD potassium cap point to the same nutrient.

Optional advanced check:

- Run live Neo4j S002 verification only if Neo4j is running locally and `.env` is configured.
- The Streamlit button now passes the USDA v3 files explicitly:
  - `data_usda_55/foods_usda_55.csv`
  - `data_v2/nutrient_constraints.csv`
  - `data_usda_55/test_scenarios_usda_90.csv`

## Page 4: Verifier Validation

Purpose: reproduce the first experiment layer.

This page answers:

> Does the deterministic verifier detect more guideline-derived findings than weaker baselines?

Recommended first scenario:

```text
S002 | HTN plus CKD hyperkalemia risk [USDA candidate]
```

Expected:

- verified = No
- violation count = 1
- conflict count = 1
- conflict nutrient = potassium_mg

Batch result source:

```text
results_usda_55/baseline_comparison_usda_90.json
```

Manuscript connection:

- Table 6
- Table 9
- Table 10

## Page 5: Multi-LLM Audit

Purpose: reproduce the second experiment layer.

This page answers:

> If LLMs receive only disease/risk information, do their recommendations satisfy executable nutrition constraints after verification?

Prompt design:

- gives disease profile,
- gives risk factors,
- gives allowed 55-food list for mapping,
- does not give potassium targets,
- does not give sodium caps,
- does not give per-food nutrient values,
- does not give verifier rules.

Saved pilot:

```text
results_v2/multi_llm_audit_usda_pilot/
```

Metrics:

```text
results_v2/multi_llm_audit_usda_pilot_metrics.md
```

Interpretation:

```text
results_v2/multi_llm_audit_usda_pilot_interpretation.md
```

Use the saved output comparison to inspect:

- raw LLM JSON,
- extracted foods,
- hard safety issue,
- soft target miss,
- violated nutrients,
- conflict nutrients.

Live API controls:

- default mode should be replay or dry-run,
- live API mini-run requires confirmation,
- keep limits small during manual checks.

## Page 6: Reproducibility

Purpose: map Streamlit outputs to manuscript tables.

Manuscript crosswalk:

| Manuscript item | Source |
|---|---|
| Table 6 | `results_usda_55/baseline_comparison_usda_90.json` |
| Table 7 | `results_v2/multi_llm_audit_usda_pilot_metrics.md/json` |
| Table 8 | `results_v2/multi_llm_audit_usda_pilot_metrics.md` |
| Table 9 | `results_usda_55/ablation_study_usda_90.md/json` |
| Figure 6 | `src_v3/experiments/generate_figure6_multillm_pipeline.py` |

## Current Verification Status

Local checks already performed:

- Streamlit app AST parse: OK
- Streamlit module import: OK
- USDA data exists: OK
- USDA S002 verifier check: 55 foods, 11 constraints, 90 scenarios, 1 violation, 1 conflict
