# Multi-LLM USDA Audit Plan

This plan separates the paper's experiments into two layers.

## Layer 1: Verifier Validation

Purpose: test whether the proposed verifier detects structured nutrition-safety problems better than weaker baselines.

Current USDA candidate inputs:

| Input | File |
|---|---|
| Food table | `data_usda_55/foods_usda_55.csv` |
| Food source mapping | `data_usda_55/food_source_mapping_usda_55.csv` |
| Scenarios | `data_usda_55/test_scenarios_usda_90.csv` |
| Constraints | `data_v2/nutrient_constraints.csv` |

Current deterministic results:

| Method | Main result |
|---|---:|
| Pure LLM | 0/90 flagged |
| Pure KG | 0/90 flagged |
| Boolean Graph-RAG | 57/90 flagged |
| RDA-only | 19/90 flagged |
| Full verifier | 73/90 flagged |
| Expected potassium conflicts | 13/13 detected |

Interpretation: this validates the engineering behavior of the verifier against executable guideline-derived constraints. It is not independent clinical outcome validation.

## Layer 2: Real LLM Output Audit

Purpose: test whether real LLM-generated recommendations vary across models and repeated runs, and whether those generated outputs require independent deterministic verification.

Initial scope:

| Dimension | Pilot setting |
|---|---|
| Models | Kimi `moonshot-v1-8k`; DeepSeek `deepseek-chat` |
| Scenario source | USDA candidate scenarios |
| Food source | USDA candidate 55-food table |
| Repeats | 3 per model per scenario for pilot |
| Scenario count | Start with 10; expand to 30 or 90 after pilot |
| Temperature | 0.7 for variability audit |
| Output format | JSON food list copied from allowed food names |

Main prompt principle:

The primary audit uses a realistic disease-only user prompt. The prompt gives the model the patient's diseases and risk factors, but it does not provide guideline nutrient thresholds, potassium targets, sodium limits, per-food nutrient values, or verifier rules. This intentionally simulates a common real-world user interaction: a user may tell the model "I have hypertension" or "I have CKD", but usually does not know the executable clinical nutrition constraints. The independent verifier is therefore needed after generation.

The allowed 55-food list is included only for experimental control and reproducible food-name mapping. It should not be interpreted as nutrition knowledge injection.

Main metrics:

| Metric | Meaning |
|---|---|
| JSON extraction rate | Whether the model followed the structured-output instruction |
| Unmatched item count | Whether it used foods outside the allowed table |
| Guideline problem rate | Fraction of generated recommendations flagged by the full verifier |
| Boolean problem rate | Fraction flagged by food-level Boolean rules |
| Expected conflict detection rate | Whether verifier detects expected conflicts in generated outputs |
| Unique recommendation count | Repeated-output variability for the same model and scenario |
| Verification outcome varied | Whether repeated outputs change pass/fail under verifier |

## API Keys Needed

For Kimi:

```powershell
$env:MOONSHOT_API_KEY="your-kimi-key"
```

For DeepSeek:

```powershell
$env:DEEPSEEK_API_KEY="your-deepseek-key"
```

Optional custom base URLs:

```powershell
$env:KIMI_API_BASE_URL="https://api.moonshot.cn/v1"
$env:DEEPSEEK_API_BASE_URL="https://api.deepseek.com"
```

## Dry-Run Check

This generates prompts only and does not call external APIs:

```powershell
python -m src_v3.experiments.run_multi_llm_audit `
  --model kimi:moonshot-v1-8k `
  --model deepseek:deepseek-chat `
  --repeats 2 `
  --limit 3 `
  --dry-run `
  --output-dir multi_llm_audit_usda_dryrun
```

Expected output:

```text
results_v2/multi_llm_audit_usda_dryrun/manifest.json
results_v2/multi_llm_audit_usda_dryrun/raw_outputs/<run_id>/<scenario_id>_prompt.txt
```

## Pilot API Run

After setting both API keys, start small:

```powershell
python -m src_v3.experiments.run_multi_llm_audit `
  --model kimi:moonshot-v1-8k `
  --model deepseek:deepseek-chat `
  --repeats 3 `
  --limit 10 `
  --output-dir multi_llm_audit_usda_pilot
```

Then generate summary metrics:

```powershell
python -m src_v3.experiments.generate_multi_llm_audit_metrics `
  --input-dir multi_llm_audit_usda_pilot `
  --output-json multi_llm_audit_usda_pilot_metrics.json `
  --output-md multi_llm_audit_usda_pilot_metrics.md
```

## Expansion Rule

Use the pilot first. Expand only if:

1. both models return parseable JSON most of the time,
2. unmatched foods are not excessive,
3. the verifier produces interpretable results,
4. repeated outputs show meaningful variability or safety differences.

Recommended expansion sequence:

| Stage | Calls |
|---|---:|
| Pilot: 2 models x 10 scenarios x 3 repeats | 60 |
| Medium: 2 models x 30 scenarios x 3 repeats | 180 |
| Full: 2 models x 90 scenarios x 3 repeats | 540 |

## Paper Integration

Recommended manuscript structure:

```text
5. Experiments
5.1 Evaluation Design
5.2 Structured USDA Benchmark for Verifier Validation
5.3 Multi-LLM Recommendation Audit
5.4 Live KG Verification and Case Study
5.5 Ablation Study
```

Layer 1 answers: can the verifier detect guideline-rule violations better than baselines?

Layer 2 answers: do real LLM outputs vary and require post-generation verification?
