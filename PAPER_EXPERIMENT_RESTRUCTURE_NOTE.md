# Paper Experiment Restructure Note

The revised paper should present the experimental system as two complementary studies.

## Study A: Structured Verifier Validation

Research question:

> Can the proposed KG-supported deterministic verifier detect guideline-derived nutrient violations and comorbidity interval conflicts better than weaker baselines?

Role in the paper:

- Validates the verification method itself.
- Uses controlled USDA candidate scenarios.
- Does not depend on LLM API variability.
- Supports reproducibility and ablation.

Recommended subsection title:

```text
5.2 Structured USDA Benchmark for Verifier Validation
```

Core results already available:

| Result | Value |
|---|---:|
| Scenarios | 90 |
| Label mismatches | 0 |
| Pure LLM flagged | 0/90 |
| Pure KG flagged | 0/90 |
| Boolean Graph-RAG flagged | 57/90 |
| RDA-only flagged | 19/90 |
| Full verifier flagged | 73/90 |
| Expected potassium conflicts detected | 13/13 |

Suggested wording:

```text
The structured benchmark evaluates the verifier's engineering consistency and
rule-detection capability under executable guideline-derived constraints. It
does not claim independent clinical diagnostic accuracy.
```

## Study B: Real LLM Recommendation Audit

Research question:

> Do real LLM-generated dietary recommendations vary across models and repeated runs, and do they require independent post-generation verification?

Role in the paper:

- Demonstrates the practical need for the verifier in the LLM era.
- Compares Kimi and DeepSeek first; additional models can be added later.
- Uses the same USDA candidate food table and verifier.
- Measures both output-format reliability and safety-verification outcomes.

Recommended subsection title:

```text
5.3 Multi-LLM Recommendation Audit
```

Pilot design:

| Design element | Value |
|---|---|
| Models | Kimi `moonshot-v1-8k`; DeepSeek `deepseek-chat` |
| Scenarios | first 10 USDA candidate scenarios |
| Repeats | 3 per model per scenario |
| API calls | 60 |
| Temperature | 0.7 |
| Output format | JSON food list copied from allowed USDA 55-food table |

Primary prompt design:

```text
The main multi-LLM audit uses a realistic disease-only prompt. The model is
told the disease profile and risk factors, but it is not given potassium
targets, sodium caps, carbohydrate/fiber thresholds, per-food nutrient values,
or verifier rules. This reflects common user-facing LLM use, where a patient
may know their diagnosis but not the executable nutrition constraints. The
allowed 55-food list is retained only to make food-name mapping reproducible.
```

Metrics:

| Metric | Purpose |
|---|---|
| JSON extraction rate | Tests structured-output reliability |
| Unmatched item count | Tests adherence to allowed food list |
| Guideline problem rate | Measures verifier-flagged generated recommendations |
| Boolean problem rate | Compares coarse food-risk rules |
| Unique recommendation count | Measures repeated-generation variability |
| Verification outcome varied | Shows whether different generations change safety outcome |

Suggested wording:

```text
The multi-LLM audit does not use LLM output as a gold standard. Instead, it
uses real model generations as candidate recommendations and applies the same
deterministic verifier to quantify format reliability, recommendation
variability, and guideline-rule violations.
```

## Manuscript Integration

Recommended Section 5 order:

```text
5. Experiments
5.1 Evaluation Design
5.2 Structured USDA Benchmark for Verifier Validation
5.3 Multi-LLM Recommendation Audit
5.4 Ablation Study
5.5 Live KG Verification and Case Study
```

Recommended Discussion emphasis:

1. The verifier is methodologically useful because it detects structured numeric violations missed by baselines.
2. The verifier is practically necessary because LLM-generated recommendations are model-dependent and may vary across repeated runs.
3. LLM fluency, JSON validity, and food-list plausibility are not equivalent to clinical nutrient safety.
4. The current claims remain prototype-level until expert clinical adjudication and larger food/guideline coverage are added.
