# USDA Multi-LLM Pilot Interpretation

Run: `multi_llm_audit_usda_pilot`

Scope:

| Dimension | Value |
|---|---:|
| Models | Kimi `moonshot-v1-8k`; DeepSeek `deepseek-chat` |
| USDA candidate scenarios | 10 |
| Repeats per model per scenario | 3 |
| Total API-backed recommendations | 60 |
| Prompt type | Disease-only realistic user prompt |

The prompt gave disease and risk-factor information but did not provide nutrient thresholds, potassium targets, sodium caps, per-food nutrient values, or verifier rules. The 55-food list was included only to make food-name mapping reproducible.

## Main Results

| Model | Completed | JSON extraction | Unmatched foods | Any verifier finding | Hard safety issue | Soft target miss | Boolean problem rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek | 30 | 1.0000 | 0 | 0.7667 | 0.1000 | 0.7667 | 0.1000 |
| Kimi | 30 | 1.0000 | 0 | 0.8667 | 0.2333 | 0.7667 | 0.3667 |

## Variability

| Metric | Value |
|---|---:|
| Scenario-model cells with repeated outputs | 20 |
| Cells with varied recommendations | 19 |
| Cells with varied verification outcomes | 4 |

This supports the claim that LLM recommendations are model-dependent and repeat-dependent even under the same disease-only prompt.

## Interpretation

The models generally followed the requested JSON format and stayed within the allowed food list. This indicates that the observed findings are not primarily parsing failures.

The models often selected foods that are directionally plausible for the disease context, such as low-sodium or potassium-rich foods for hypertension. However, serving-weighted nutrient totals frequently missed executable therapeutic targets, especially potassium, carbohydrate, and fiber. These should be described as soft target misses, not necessarily hard safety violations.

Hard safety issues were less frequent but clinically more important. In this pilot, hard issues were associated with comorbidity potassium conflicts, CKD potassium or phosphorus restrictions, and meal-level sodium limits.

The key paper-level conclusion is:

```text
LLMs can often capture common dietary advice at the semantic level, but they do
not reliably satisfy executable guideline-derived nutrient constraints. A
post-generation verifier is therefore useful both for identifying hard safety
issues and for distinguishing them from softer therapeutic target misses.
```

