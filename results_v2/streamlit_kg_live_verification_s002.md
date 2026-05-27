# Live Neo4j KG Verification

Live Neo4j KG verification artifact generated from configured CSV-backed graph data.

## Connection

- URI: `neo4j://localhost:7687`
- Database: `nutrition`
- Connectivity check: `True`
- Imported this run: `True`

## Data Sources

- Foods CSV: `D:\claude\study\paper\nutrition-graph-rag-github-ready\data_usda_55\foods_usda_55.csv`
- Constraints CSV: `D:\claude\study\paper\nutrition-graph-rag-github-ready\data_v2\nutrient_constraints.csv`
- Scenarios CSV: `D:\claude\study\paper\nutrition-graph-rag-github-ready\data_usda_55\test_scenarios_usda_90.csv`

## Scenario

- Scenario: `S002`
- Name: HTN plus CKD hyperkalemia risk [USDA candidate]
- Diseases: HTN, CKD
- Risk factors: hyperkalemia_risk
- Recommended foods: Oatmeal, Broccoli, Spinach, Banana, Lentils cooked

## Live Schema Counts

| Node count | Value |
|---|---:|
| food_count | 55 |
| disease_count | 3 |
| nutrient_count | 10 |
| constraint_count | 11 |
| guideline_count | 4 |
| risk_factor_count | 3 |

| Edge count | Value |
|---|---:|
| food_contains_nutrient | 550 |
| disease_has_constraint | 11 |
| constraint_on_nutrient | 11 |
| derived_from_guideline | 11 |
| risk_factor_activates_constraint | 3 |

## Active Constraints Retrieved by Cypher

| Constraint | Disease | Nutrient | Lower | Upper | Unit | Condition | Priority | Source | Activating risks |
|---|---|---|---:|---:|---|---|---|---|---|
| C_CKD_K_001 | CKD | potassium_mg |  | 2000.0 | mg/day | CKD on dialysis or with hyperkalemia risk (serum K >5.0 mEq/L) | safety-critical | KDIGO 2024 CKD Guidelines / KDOQI 2020 Nutrition Guidelines | hyperkalemia_risk |
| C_CKD_NA_001 | CKD | sodium_mg |  | 2000.0 | mg/day | all CKD stages | disease-therapeutic | KDIGO 2024 CKD Guidelines / KDOQI 2020 Nutrition Guidelines | none |
| C_HTN_K_001 | HTN | potassium_mg | 3500.0 | 5000.0 | mg/day | adult hypertension patient without potassium restriction | disease-therapeutic | ACC/AHA 2017 Hypertension Guidelines | none |
| C_HTN_NA_001 | HTN | sodium_mg |  | 2300.0 | mg/day | adult hypertension general sodium target | disease-therapeutic | ACC/AHA 2017 Hypertension Guidelines | none |
| C_HTN_NA_002 | HTN | sodium_mg |  | 1500.0 | mg/day | confirmed hypertension or high cardiovascular risk | disease-therapeutic | ACC/AHA 2017 Hypertension Guidelines | none |

## Risk-Factor Activations

| Risk factor | Disease | Activated constraint | Condition |
|---|---|---|---|
| hyperkalemia_risk | CKD | C_CKD_K_001 | CKD on dialysis or with hyperkalemia risk (serum K >5.0 mEq/L) |

## Potassium Interval Check

| Nutrient | Constraints | Merged lower | Merged upper | Conflict detected |
|---|---|---:|---:|---|
| potassium_mg | C_CKD_K_001, C_HTN_K_001 | 3500.0 | 2000.0 | True |

## Retrieved Food Nutrient Profiles

| Food | Category | Serving size (g) | Nutrient edges |
|---|---|---:|---:|
| Banana | fruit | 120.0 | 20 |
| Broccoli | vegetable | 100.0 | 20 |
| Lentils cooked | legume | 100.0 | 20 |
| Oatmeal | grain | 40.0 | 20 |
| Spinach | vegetable | 100.0 | 20 |

## Guideline Provenance

| Constraint | Guideline | Source |
|---|---|---|
| C_CKD_K_001 | G_CKD_001 | KDIGO 2024 CKD Guidelines / KDOQI 2020 Nutrition Guidelines |
| C_CKD_NA_001 | G_CKD_001 | KDIGO 2024 CKD Guidelines / KDOQI 2020 Nutrition Guidelines |
| C_HTN_K_001 | G_HTN_001 | ACC/AHA 2017 Hypertension Guidelines |
| C_HTN_NA_001 | G_HTN_001 | ACC/AHA 2017 Hypertension Guidelines |
| C_HTN_NA_002 | G_HTN_001 | ACC/AHA 2017 Hypertension Guidelines |
