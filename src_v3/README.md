# src_v2

This directory contains the clean v2 implementation for the paperCodeX direction.

The old `src/` demo is intentionally left untouched. This v2 code focuses on:

- explicit `ClinicalGuideline` and `NutrientConstraint` graph entities;
- deterministic nutrient-range verification;
- interval-intersection conflict detection;
- evidence traceability reports;
- experiment-ready baselines.

## First milestone

Run the v2 logic on a small local data set before wiring every path into the UI:

```powershell
python -m src_v2.experiments.run_experiments
```

The initial experiment runner uses CSV templates under `data_v2/` and does not require Neo4j. Neo4j import/query modules are included for the next step.

To save a structured result file for manuscript tables:

```powershell
python -m src_v2.experiments.run_experiments --output-json smoke_results.json
```

To run the current assertions for the core case:

```powershell
python -m src_v2.experiments.smoke_test
```

The current smoke test checks that:

- HTN alone does not trigger a CKD potassium restriction;
- HTN + CKD with hyperkalemia risk detects the potassium interval conflict;
- the same multimorbidity scenario reports a CKD potassium upper-bound violation;
- a CKD high-sodium scenario reports a sodium upper-bound violation.

To run the first-pass baseline comparison:

```powershell
python -m src_v2.experiments.run_baseline_comparison
```

To generate real LLM baseline prompts without API calls:

```powershell
python -m src_v2.experiments.run_real_llm_baseline --dry-run --limit 2
```

To call a configured LLM and store raw outputs plus extracted foods:

```powershell
python -m src_v2.experiments.run_real_llm_baseline --provider kimi --limit 5
```

The expanded 90-scenario Kimi run was generated with:

```powershell
python -m src_v2.experiments.run_real_llm_baseline --provider kimi --output-json real_llm_baseline_90.json --raw-output-dir real_llm_raw_outputs_90 --sleep-seconds 0.5
```

To generate metrics from a real LLM run:

```powershell
python -m src_v2.experiments.generate_real_llm_metrics --input-json real_llm_baseline_30_replayed.json --output-json real_llm_metrics_30_replayed.json --output-md real_llm_metrics_30_replayed.md
```

For the expanded 90-scenario run:

```powershell
python -m src_v2.experiments.generate_real_llm_metrics --input-json real_llm_baseline_90.json --output-json real_llm_metrics_90.json --output-md real_llm_metrics_90.md
```

To generate paper-oriented error analysis:

```powershell
python -m src_v2.experiments.generate_real_llm_error_analysis --input-json real_llm_baseline_30_replayed.json --output-json real_llm_error_analysis_30_replayed.json --output-md real_llm_error_analysis_30_replayed.md
```

For the expanded 90-scenario run:

```powershell
python -m src_v2.experiments.generate_real_llm_error_analysis --input-json real_llm_baseline_90.json --output-json real_llm_error_analysis_90.json --output-md real_llm_error_analysis_90.md
```

To run the 90-scenario verifier ablation study:

```powershell
python -m src_v2.experiments.run_ablation_study --output-json ablation_study_90.json --output-md ablation_study_90.md
```

## Current data scope

The current prototype data set is:

- 55 foods in `data_v2/foods_extended.csv`;
- 11 guideline-derived constraints in `data_v2/nutrient_constraints.csv`;
- 90 test scenarios in `data_v2/test_scenarios.csv`.

The scenario CSV includes explicit expected-label columns:

```text
expected_passed
expected_violation_nutrients
expected_conflict_nutrient
expected_missing_data
label_source
```

To validate those labels against the current verifier:

```powershell
python -m src_v2.experiments.validate_scenario_labels --output-json scenario_label_validation_90.json --fail-on-mismatch
```

To generate a reproducible KG retrieval artifact for the canonical HTN + CKD
conflict case:

```powershell
python -m src_v2.experiments.generate_kg_retrieval_artifact --scenario-id S002 --output-json kg_retrieval_artifact_s002.json --output-md kg_retrieval_artifact_s002.md
```

To run live Neo4j import and query verification after starting Neo4j:

```powershell
python -m src_v2.experiments.run_kg_live_verification --uri bolt://localhost:7687 --scenario-id S002 --output-json kg_live_verification_s002.json --output-md kg_live_verification_s002.md
```

The command imports the current CSV-backed graph data with `MERGE`, then saves
active constraint retrieval, risk-factor activation, food nutrient retrieval,
guideline provenance, and the S002 potassium interval check under `results_v2/`.
If Neo4j is not running or the Bolt URI/database is wrong, the command writes a
diagnostic artifact instead of partial live-query results.

The guideline rows have received an initial conservative audit. Before final
manuscript submission, the final numeric values, wording, and clinical scope
should still be checked against source guidelines and cited precisely.
