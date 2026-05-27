# Manuscript Data Source Note

This note can be adapted for the Methods or Data section if the USDA candidate
dataset becomes the main experimental dataset.

## Food Composition Source

The 55-food experimental table was constructed from locally downloaded USDA
FoodData Central CSV datasets. Each food item was mapped to a USDA FDC entry and
the selected FDC identifier, source dataset, source description, and publication
date were recorded in `food_source_mapping_usda_55.csv`.

Primary nutrient fields were extracted from USDA FoodData Central per-100 g
values and converted to the serving sizes used by the verifier:

- energy
- protein
- carbohydrate
- total fat
- dietary fiber
- sodium
- potassium
- phosphorus

For FNDDS/Survey entries, nutrient-number identifiers were mapped to the same
analysis fields before serving-size conversion.

## Non-USDA or Imputed Fields

USDA FoodData Central does not provide glycemic index as a standard nutrient
field. GI values in `foods_usda_55.csv` are therefore proxy values retained for
compatibility with the existing schema. They should not be described as USDA
measurements and should not be used as source-validated primary outcomes.

Added sugar is unavailable for many selected USDA entries. Missing added-sugar
values were imputed as zero and explicitly marked in
`food_source_mapping_usda_55.csv`. This is most defensible for unprocessed foods
but should be treated cautiously for composite and processed foods.

## Recommended Wording

Food composition values were derived from USDA FoodData Central candidate
entries with explicit FDC identifiers recorded for each item. Nutrients not
available as standard USDA FDC fields, including glycemic index, were retained
only as proxy attributes and were not treated as source-validated nutrient
measurements.
