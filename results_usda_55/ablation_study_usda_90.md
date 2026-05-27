# Ablation Study

## Important Limitation

This ablation uses the structured 90-scenario prototype set and scenario-design labels. It evaluates verifier modules, not an independently adjudicated clinical benchmark.

## Variant Metrics

| Variant | Passed | Problems Detected | Problem Detection Rate | Expected Unsafe Detection Rate | Expected Conflicts Detected | Expected Conflict Detection Rate | Evidence Traceability Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full system | 17 | 73 | 0.8111 | 1.0000 | 13/13 | 1.0000 | 1.0000 |
| w/o nutrient-range verification | 77 | 13 | 0.1444 | 0.1781 | 13/13 | 1.0000 | 1.0000 |
| w/o conflict detection | 17 | 73 | 0.8111 | 1.0000 | 0/13 | 0.0000 | 1.0000 |
| w/o evidence provenance | 17 | 73 | 0.8111 | 1.0000 | 13/13 | 1.0000 | 0.0000 |
| RDA-only constraints | 71 | 19 | 0.2111 | 0.2603 | 0/13 | 0.0000 | 1.0000 |

## Delta vs Full System

| Variant | Lost Problem Detections | Lost Expected Conflict Detections | Lost Traceable Reports |
|---|---:|---:|---:|
| w/o nutrient-range verification | 60 | 0 | 60 |
| w/o conflict detection | 0 | 13 | 0 |
| w/o evidence provenance | 0 | 0 | 73 |
| RDA-only constraints | 54 | 13 | 54 |

## Metric Definitions

- `problem_detection_rate`: scenarios flagged by the variant / all scenarios
- `expected_unsafe_detection_rate`: expected unsafe scenarios flagged by the variant / expected unsafe scenarios
- `expected_conflict_detection_rate`: expected conflict scenarios with the expected nutrient conflict detected / expected conflict scenarios
- `evidence_traceability_rate`: problem reports with at least one guideline evidence source / problem reports
