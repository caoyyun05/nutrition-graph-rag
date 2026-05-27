# Nutrient Constraint Decisions

Last updated: 2026-05-17

This file records policy decisions for revising `nutrient_constraints.csv` after
the initial evidence audit. The default strategy is conservative:

```text
- Keep the prototype runnable.
- Preserve the HTN + CKD potassium conflict case.
- Do not present operational prototype thresholds as universal clinical rules.
- Remove or soften bounds that are not directly supported as fixed guideline
  limits.
- Make source and note fields explicit about what is guideline-supported and
  what is operationalized for the prototype.
```

## Decision 1. HTN Potassium Upper Bound

Question:

```text
Should HTN potassium upper_bound remain 4700 mg/day, or change to 5000 mg/day?
```

Evidence summary:

```text
ACC/AHA 2017 supports dietary potassium 3500-5000 mg/day unless contraindicated
by CKD or drugs that reduce potassium excretion. The current 4700 value is common
in DASH/DRI-style targets, but the checked ACC/AHA source supports 5000 as the
upper range value.
```

Conservative decision:

```text
Change upper_bound from 4700 to 5000 and cite ACC/AHA 2017.
```

Impact:

```text
S002 remains a potassium conflict because CKD operational cap remains 2000.
```

Status:

```text
adopted
```

## Decision 2. CKD Potassium 2000 mg/day

Question:

```text
Should CKD potassium upper_bound=2000 be retained?
```

Evidence summary:

```text
KDIGO 2024 and KDOQI 2020 support individualized potassium management for CKD
patients with hyperkalemia or hyperkalemia risk. They do not clearly establish a
universal 2000 mg/day dietary potassium cap in the checked text.
```

Conservative decision:

```text
Keep 2000 mg/day as an operational prototype threshold for CKD patients with
hyperkalemia risk or dialysis-related risk. Do not describe it as a universal
KDIGO/KDOQI rule.
```

Impact:

```text
This preserves the core HTN + CKD potassium conflict case, while keeping the
paper wording clinically cautious.
```

Status:

```text
adopted as operational threshold
```

## Decision 3. CKD Potassium 3000 mg/day

Question:

```text
Should CKD potassium upper_bound=3000 for pre-dialysis CKD without hyperkalemia
remain in the formal constraint set?
```

Evidence summary:

```text
KDIGO/KDOQI emphasize individualized potassium management and caution against
unnecessary broad potassium restriction without hyperkalemia risk.
```

Conservative decision:

```text
Remove this row from formal active constraints for now.
```

Impact:

```text
Reduces over-constraint of CKD patients without hyperkalemia risk. S006 should
continue to avoid potassium conflict.
```

Status:

```text
adopted
```

## Decision 4. CKD Sodium 1500 mg/day

Question:

```text
Should CKD sodium upper_bound=1500 for CKD with comorbid hypertension or edema
remain as a separate CKD constraint?
```

Evidence summary:

```text
KDIGO 2024 supports sodium intake <2 g/day in CKD. The 1500 mg/day target is more
clearly supported by AHA/ACC hypertension guidance as an ideal or optimal sodium
goal for elevated BP or hypertension, not as a CKD-specific KDIGO target.
```

Conservative decision:

```text
Remove the separate CKD 1500 mg/day row. Let HTN sodium constraints activate the
stricter 1500 mg/day value when HTN is selected alongside CKD.
```

Impact:

```text
Avoids double-counting sodium violations from CKD and HTN. CKD-only sodium
testing uses 2000 mg/day.
```

Status:

```text
adopted
```

## Decision 5. T2DM Fiber Upper Bound

Question:

```text
Should T2DM fiber keep upper_bound=35 g/day?
```

Evidence summary:

```text
ADA 2024 supports high-fiber carbohydrate sources and at least 14 g fiber per
1000 kcal. It does not support treating 35 g/day as a violation upper limit.
```

Conservative decision:

```text
Remove upper_bound=35. Keep a lower fiber adequacy target. Use 28 g/day for a
2000 kcal reference diet based on 14 g/1000 kcal.
```

Impact:

```text
S010 should no longer fail because of high fiber. Some low-fiber T2DM scenarios
may still fail.
```

Status:

```text
adopted
```

## Decision 6. T2DM Carbohydrate Bounds

Question:

```text
Should T2DM carbohydrate keep lower_bound=130 and upper_bound=300?
```

Evidence summary:

```text
ADA 2024 emphasizes individualized carbohydrate intake and does not endorse one
fixed macronutrient interval. The 130 g/day value is a general DRI/RDA adequacy
floor, while 300 g/day is a 2000 kcal reference-diet upper value rather than an
ADA diabetes-specific upper limit.
```

Conservative decision:

```text
Keep lower_bound=130 as a soft general adequacy floor and remove upper_bound=300.
Revise source/note to clarify that the lower bound comes from DRI, while ADA
supports individualized carbohydrate management.
```

Impact:

```text
Reduces overclaiming. The verifier still detects very low carbohydrate scenarios
when this adequacy floor is active.
```

Status:

```text
adopted
```

## Decision 7. Meaning of hard / safety-critical

Question:

```text
Should hard/safety-critical mean clinical emergency risk or prototype rejection
rule?
```

Conservative decision:

```text
Use the labels as system-level verification severity, not as direct clinical
emergency labels.
```

Operational interpretation:

```text
hard
    The prototype should reject or flag the recommendation as not verified.

safety-critical
    A high-priority nutrition safety concern in the prototype, especially for
    kidney-related electrolyte constraints.

disease-therapeutic
    Disease-management target, generally less urgent than kidney electrolyte
    safety gates.
```

Impact:

```text
The manuscript must state that these are verification severity labels, not
clinical diagnosis or treatment urgency labels.
```

Status:

```text
adopted
```

