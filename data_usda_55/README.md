# USDA 55 Candidate Dataset

This directory is a parallel candidate dataset. It does not replace
`data_v2/foods_extended.csv`.

## Files

- `foods_usda_55.csv`: 55-food table with the same schema used by the current
  verifier.
- `food_source_mapping_usda_55.csv`: source metadata for each selected USDA
  FoodData Central entry.
- `food_candidate_review_usda_55.csv`: selected candidate plus top alternatives
  for manual review.
- `foods_usda_55_audit.md`: human-readable audit summary and review flags.
- `foods_usda_55_build.json`: full build artifact from the generator.

## Current Status

This dataset is suitable for local deterministic trial runs after the experiment
scripts are parameterized to accept an alternate food CSV.

It is not yet a final manuscript dataset because:

- Candidate matching still has manual-review flags.
- GI is not provided by USDA FoodData Central and is stored as a proxy field.
- Added sugar is missing for many USDA entries and is currently imputed as zero
  where unavailable.

## Recommended Next Step

Keep the current v2 submission data as fallback. Use this directory to build a
separate USDA experiment path:

1. Parameterize experiment scripts to accept `--foods-csv`.
2. Generate a USDA-specific scenario CSV or replay a small subset first.
3. Validate labels before changing manuscript tables.
4. Only update the paper if deterministic results remain coherent.
