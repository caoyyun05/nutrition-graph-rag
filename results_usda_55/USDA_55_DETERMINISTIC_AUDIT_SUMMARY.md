# USDA 55 Deterministic Audit Summary

Date: 2026-05-26

This directory contains a parallel deterministic experiment run using
`data_usda_55/foods_usda_55.csv` and
`data_usda_55/test_scenarios_usda_90.csv`.

The original v2 submission files were not overwritten.

## Inputs

- Food table: `data_usda_55/foods_usda_55.csv`
- Source mapping: `data_usda_55/food_source_mapping_usda_55.csv`
- Scenario table: `data_usda_55/test_scenarios_usda_90.csv`
- Constraints: `data_v2/nutrient_constraints.csv`

## Outputs

- `scenario_label_validation_usda_90.json`
- `baseline_comparison_usda_90.json`
- `ablation_study_usda_90.json`
- `ablation_study_usda_90.md`

## Deterministic Results

| Check | Result |
|---|---:|
| Scenario count | 90 |
| Scenario label mismatches | 0 |
| Guideline-constrained failures | 73/90 |
| Guideline-constrained problem detection rate | 0.8111 |
| Expected conflict scenarios detected | 13/13 |
| Expected conflict detection rate | 1.0000 |
| Boolean Graph-RAG problem detections | 57/90 |
| Pure LLM problem detections | 0/90 |
| Pure KG problem detections | 0/90 |

The deterministic results remained stable after replacing earlier weak
candidate matches for oatmeal, cottage cheese, and chocolate cake with more
appropriate USDA entries.

## Ablation Results

| Variant | Problem detection rate | Expected conflict detection rate | Evidence traceability rate |
|---|---:|---:|---:|
| Full system | 0.8111 | 1.0000 | 1.0000 |
| w/o nutrient-range verification | 0.1444 | 1.0000 | 1.0000 |
| w/o conflict detection | 0.8111 | 0.0000 | 1.0000 |
| w/o evidence provenance | 0.8111 | 1.0000 | 0.0000 |
| RDA-only constraints | 0.2111 | 0.0000 | 1.0000 |

## Cautions

- This is a candidate dataset, not yet the final manuscript dataset.
- USDA FDC does not provide GI; GI values in the food CSV are proxies.
- Added sugar is unavailable for many entries and is imputed as zero.
- Several food candidates are flagged for manual review in
  `data_usda_55/foods_usda_55_audit.md`.

Current remaining candidate-level caveats:

- `Soda` is represented by the USDA SR Legacy entry for cream soda, i.e., a
  sugar-sweetened carbonated beverage rather than cola specifically.
- `Sweetened cereal` is represented by a specific USDA SR Legacy ready-to-eat
  sweetened cereal entry.

## Manuscript Implication

If this USDA path is adopted, manuscript experiment tables must be updated from
the v2 values. In particular, the deterministic guideline-constrained failure
count changes from the previous v2 audit result to 73/90 under the USDA
candidate food table.
