# Nutrient Constraints Audit

Last updated: 2026-05-17

This file audits `data_v2/nutrient_constraints.csv` against guideline and
nutrition reference sources. It is a working evidence table, not a clinical
recommendation document.

Status labels:

```text
verified          Current bound is directly or reasonably supported.
revise            Current row is close but should be edited before manuscript use.
needs decision    Current row is useful for the prototype, but the numeric bound
                  or clinical scope is not directly supported by the cited guideline.
remove candidate  Current row may be better removed from the formal constraint set.
```

## Sources Checked

Primary sources and references used in this audit:

```text
ACC/AHA 2017 High Blood Pressure Guideline slide set
https://professional.heart.org/en/-/media/PHD-Files-2/Science-News/2/2017/2017_AHA_ACC_Hypertenson_Clinical_Guidelines_ucm_497372.pdf

American Heart Association sodium guidance
https://www.heart.org/en/healthy-living/healthy-eating/eat-smart/sodium/how-to-track-your-sodium
https://www.heart.org/en/health-topics/high-blood-pressure/changes-you-can-make-to-manage-high-blood-pressure/shaking-the-salt-habit-to-lower-high-blood-pressure

KDIGO 2024 CKD Guideline
https://kdigo.org/wp-content/uploads/2024/03/KDIGO-2024-CKD-Guideline.pdf

KDOQI Clinical Practice Guideline for Nutrition in CKD: 2020 Update
https://www.sciencedirect.com/science/article/pii/S0272638620307265
https://files.medelement.com/uploads/materials/13f2bc11c816b9d17ac3bb29c4081c11.pdf

ADA Standards of Care in Diabetes 2024, Section 5
DOI: 10.2337/dc24-S005
https://www.bluecirclehealth.org/wp-content/uploads/2023/06/ADA_SoC_ch5.pdf

Dietary Guidelines / FDA added sugars reference
https://www.fda.gov/food/nutrition-facts-label/added-sugars-nutrition-facts-label

National Academies Dietary Reference Intakes for carbohydrate
https://nap.nationalacademies.org/read/10490/chapter/8
```

Important evidence notes:

```text
- ACC/AHA 2017 supports sodium reduction, an optimal sodium goal of <1500 mg/day,
  and dietary potassium 3500-5000 mg/day unless contraindicated by CKD or drugs
  reducing potassium excretion.
- KDIGO 2024 supports sodium intake <2 g/day in people with CKD and individualized
  potassium management for CKD G3-G5 with hyperkalemia.
- KDOQI 2020 supports individualized phosphorus and potassium management; it
  discusses traditional phosphorus ranges of 800-1000 mg/day but explicitly notes
  that exact phosphorus ranges are not well established.
- ADA 2024 supports individualized meal plans, no single macronutrient pattern,
  high-fiber carbohydrate sources at least 14 g fiber/1000 kcal, minimizing added
  sugars, and sodium <2300 mg/day.
```

## Constraint-by-Constraint Audit

### C_HTN_NA_001

Current row:

```text
HTN, sodium_mg, upper_bound=2300, soft, disease-therapeutic
```

Evidence:

```text
AHA public sodium guidance supports no more than 2300 mg/day and an ideal goal
of no more than 1500 mg/day for most adults. ACC/AHA 2017 hypertension guidance
emphasizes sodium reduction and lists <1500 mg/day as the optimal goal.
```

Assessment:

```text
2300 mg/day is supportable as a general upper limit, but the current source should
not rely only on ACC/AHA 2017 if the row is framed as a general sodium ceiling.
```

Recommended action:

```text
Keep upper_bound=2300.
Revise source to include AHA sodium guidance or Dietary Guidelines for Americans.
Keep as soft.
```

Status:

```text
revise
```

### C_HTN_NA_002

Current row:

```text
HTN, sodium_mg, upper_bound=1500, hard, safety-critical
```

Evidence:

```text
ACC/AHA 2017 lists an optimal sodium goal of <1500 mg/day for adults with elevated
BP or hypertension. AHA public hypertension sodium guidance also states an ideal
limit of 1500 mg/day, especially for people with high blood pressure.
```

Assessment:

```text
The 1500 mg/day target is supported. The hard/safety-critical classification is
stricter than the guideline language and is a system-design decision.
```

Recommended action:

```text
Keep upper_bound=1500 for high-risk HTN experiments.
Consider changing priority from safety-critical to disease-therapeutic unless the
paper explicitly defines "hard" as prototype safety gating rather than clinical
emergency risk.
```

Status:

```text
needs decision
```

### C_HTN_K_001

Current row:

```text
HTN, potassium_mg, lower_bound=3500, upper_bound=4700, soft, disease-therapeutic
```

Evidence:

```text
ACC/AHA 2017 recommends dietary potassium 3500-5000 mg/day for adults with
elevated BP or hypertension, preferably from a potassium-rich diet, unless
contraindicated by CKD or drugs that reduce potassium excretion.
```

Assessment:

```text
The lower bound 3500 is supported. The current upper bound 4700 is not the ACC/AHA
upper value; ACC/AHA uses 5000. The 4700 value may come from DASH/National
Academies style targets, but it needs an explicit source if retained.
```

Recommended action:

```text
Option A: revise upper_bound to 5000 and cite ACC/AHA 2017.
Option B: keep upper_bound=4700, but cite a source that specifically supports 4700.
Keep the CKD contraindication note because it is directly supported by ACC/AHA.
```

Status:

```text
needs decision
```

### C_CKD_NA_001

Current row:

```text
CKD, sodium_mg, upper_bound=2000, all CKD stages, hard, safety-critical
```

Evidence:

```text
KDIGO 2024 suggests sodium intake <2 g/day in people with CKD. KDOQI 2020
recommends limiting sodium to <100 mmol/day, or <2.3 g/day, for adults with CKD
3-5, CKD 5D, or posttransplantation to reduce blood pressure and improve volume
control.
```

Assessment:

```text
The 2000 mg/day bound is supported by KDIGO 2024. It is stricter than KDOQI 2020.
The "all CKD stages" wording should include relevant exceptions, such as
sodium-wasting nephropathy noted by KDIGO.
```

Recommended action:

```text
Keep upper_bound=2000.
Revise note to mention KDIGO 2024 and exception for sodium-wasting nephropathy.
Consider changing hard/safety-critical to hard/disease-therapeutic unless the
paper defines sodium as a safety gate.
```

Status:

```text
revise
```

### C_CKD_NA_002

Current row:

```text
CKD, sodium_mg, upper_bound=1500, CKD with comorbid hypertension or edema,
hard, safety-critical
```

Evidence:

```text
KDIGO 2024 supports <2 g/day sodium in CKD. ACC/AHA/AHA support <1500 mg/day as
an optimal or ideal sodium target for elevated BP or hypertension. I did not find
a KDIGO 2024 statement that directly assigns 1500 mg/day to CKD with comorbid
hypertension or edema.
```

Assessment:

```text
The row is clinically plausible as a stricter operational target when CKD is
combined with hypertension, but the current source "KDIGO 2024" alone is too
strong for the 1500 mg/day number.
```

Recommended action:

```text
Either:
1. Keep upper_bound=1500 as an operational comorbidity target and cite ACC/AHA/AHA
   in addition to KDIGO; or
2. Remove this row and let C_CKD_NA_001 plus HTN sodium constraints handle the
   stricter target when HTN is selected.
```

Status:

```text
needs decision
```

### C_CKD_K_001

Current row:

```text
CKD, potassium_mg, upper_bound=2000, CKD on dialysis or with hyperkalemia risk,
hard, safety-critical
```

Evidence:

```text
KDIGO 2024 recommends individualized dietary and pharmacologic intervention for
CKD G3-G5 with emergent hyperkalemia and advises limiting foods rich in
bioavailable potassium for people with CKD G3-G5 who have a history of
hyperkalemia or periods of hyperkalemia risk.

KDOQI 2020 says dietary potassium should be adjusted to maintain serum potassium
within the normal range, and for hyperkalemia or hypokalemia, potassium intake
should be based on individual needs and clinician judgment.
```

Assessment:

```text
The condition-aware potassium restriction is supported. The fixed 2000 mg/day
upper bound is not directly stated by KDIGO/KDOQI in the checked text. It is best
treated as an operational prototype threshold unless another renal diet source is
added.
```

Recommended action:

```text
Keep temporarily for the HTN+CKD conflict prototype, but revise note to say:
"Operational potassium cap for prototype verification in CKD with hyperkalemia
risk; KDIGO/KDOQI emphasize individualized potassium management rather than a
universal fixed limit."
```

Status:

```text
needs decision
```

### C_CKD_K_002

Current row:

```text
CKD, potassium_mg, upper_bound=3000, CKD pre-dialysis G3-G4 without hyperkalemia,
soft, disease-therapeutic
```

Evidence:

```text
KDOQI 2020 supports individualized potassium adjustment. KDIGO 2024 warns against
unnecessary broad potassium restriction and focuses restriction on hyperkalemia
history or risk periods.
```

Assessment:

```text
The fixed 3000 mg/day upper bound for pre-dialysis CKD without hyperkalemia is
not directly supported by the checked guideline statements.
```

Recommended action:

```text
Option A: remove this row from the formal manuscript constraint set.
Option B: keep as a soft operational sensitivity threshold, clearly labeled as
prototype-only.
```

Status:

```text
needs decision
```

### C_CKD_P_001

Current row:

```text
CKD, phosphorus_mg, upper_bound=800, CKD on dialysis or with hyperphosphatemia,
hard, safety-critical
```

Evidence:

```text
KDOQI 2020 recommends adjusting dietary phosphorus intake to maintain serum
phosphate in the normal range and considering phosphorus source bioavailability.
It notes that traditional CKD-specific recommendations suggest 800-1000 mg/day,
but also states that the efficacy of this exact range is not established and
prefers individualized treatment. One cited dialysis counseling trial targeted
800-900 mg/day.
```

Assessment:

```text
The 800 mg/day value is plausible for a strict dialysis/hyperphosphatemia
prototype threshold, but KDOQI does not present it as a universal hard guideline
limit.
```

Recommended action:

```text
Keep only if labeled as an operational strict threshold for hyperphosphatemia or
dialysis case testing. Revise note to reflect KDOQI's individualized approach and
source-bioavailability emphasis.
```

Status:

```text
needs decision
```

### C_CKD_P_002

Current row:

```text
CKD, phosphorus_mg, upper_bound=1000, CKD pre-dialysis with elevated serum
phosphorus, soft, disease-therapeutic
```

Evidence:

```text
KDOQI 2020 discusses traditional phosphorus intake ranges of 800-1000 mg/day for
CKD stages 3-5 and maintenance dialysis, but says exact ranges are not well
established and treatment should be individualized.
```

Assessment:

```text
The 1000 mg/day value is defensible as a traditional soft target, not as a hard
guideline-derived upper bound.
```

Recommended action:

```text
Keep as soft if note explicitly says "traditional range / operational target" and
not "KDOQI mandates 1000 mg/day."
```

Status:

```text
revise
```

### C_T2DM_NA_001

Current row:

```text
T2DM, sodium_mg, upper_bound=2300, soft, disease-therapeutic
```

Evidence:

```text
ADA 2024 recommendation 5.25 counsels people with diabetes to limit sodium
consumption to <2300 mg/day.
```

Assessment:

```text
The bound and source are supported.
```

Recommended action:

```text
Keep as is, with exact ADA 2024 section/recommendation noted in source or note.
```

Status:

```text
verified
```

### C_T2DM_FIB_001

Current row:

```text
T2DM, fiber_g, lower_bound=25, upper_bound=35, soft, disease-therapeutic
```

Evidence:

```text
ADA 2024 recommends minimally processed, nutrient-dense, high-fiber carbohydrate
sources at least 14 g fiber per 1000 kcal. It also states higher-fiber diets are
advantageous and encourages at least 14 g fiber/1000 kcal.
```

Assessment:

```text
The lower target is supported in principle. For a 2000 kcal reference diet,
14 g/1000 kcal maps to about 28 g/day. A lower_bound of 25 g/day is close to
common DRI-style female adult adequate intake, but it is not the exact ADA 2024
calculation for 2000 kcal. The upper_bound=35 is not supported as an ADA upper
limit and is causing S010 to fail.
```

Recommended action:

```text
Remove upper_bound=35, or convert the row into a target-range display rather than
a violation rule. Consider lower_bound=28 for a 2000 kcal reference diet if using
ADA 14 g/1000 kcal directly.
```

Status:

```text
needs decision
```

### C_T2DM_CARB_001

Current row:

```text
T2DM, carbohydrate_g, lower_bound=130, upper_bound=300, soft, disease-therapeutic
```

Evidence:

```text
ADA 2024 says meal plans should be individualized and data do not support one
specific macronutrient pattern. ADA also says reducing overall carbohydrate
intake may improve glycemia for adults with diabetes.

The 130 g/day lower bound is a Dietary Reference Intake RDA for carbohydrate
based on brain glucose utilization. The 300 g/day upper bound corresponds to a
Nutrition Facts Daily Value / 60% of a 2000 kcal reference diet, not a diabetes
specific ADA upper limit.
```

Assessment:

```text
The current row mixes a general-population DRI lower bound with a reference-diet
upper bound. It should not be presented as an ADA 2024 T2DM-specific carbohydrate
interval.
```

Recommended action:

```text
Option A: remove upper_bound=300 and keep lower_bound=130 as a general DRI-based
adequacy floor, not a diabetes-specific treatment target.
Option B: remove this constraint from the formal verifier and treat carbohydrate
as a descriptive metric unless a clear scenario-specific carbohydrate target is
defined.
```

Status:

```text
needs decision
```

### C_T2DM_SUGAR_001

Current row:

```text
T2DM, added_sugar_g, upper_bound=50, soft, disease-therapeutic
```

Evidence:

```text
ADA 2024 recommends minimizing foods with added sugar that displace healthier,
more nutrient-dense choices. FDA/Dietary Guidelines guidance maps the <10% of
calories added-sugar recommendation to 50 g/day for a 2000 kcal diet.
```

Assessment:

```text
The 50 g/day value is supportable as a 2000 kcal DGA/FDA operational threshold,
but not as an ADA-specific fixed diabetes limit.
```

Recommended action:

```text
Keep as soft. Revise source/note to cite DGA/FDA for the numeric 50 g/day value
and ADA 2024 for the diabetes-specific recommendation to minimize added sugars.
```

Status:

```text
revise
```

## Decisions Needed

Please confirm the following before I revise `nutrient_constraints.csv`:

```text
1. HTN potassium upper bound:
   Change 4700 to 5000 using ACC/AHA 2017, or keep 4700 with an additional DASH/
   National Academies source?

2. CKD potassium 2000 mg/day:
   Keep as an operational prototype threshold for hyperkalemia-risk cases, or
   remove fixed potassium caps and only report condition-aware warnings?

3. CKD potassium 3000 mg/day:
   Remove from formal constraints, or keep as a soft prototype sensitivity
   threshold?

4. CKD sodium 1500 mg/day:
   Keep as a comorbid HTN operational target, or remove and let HTN sodium
   constraints handle the stricter value?

5. T2DM fiber:
   Remove upper_bound=35 to make high fiber non-violating, or keep 25-35 as a
   target range display only?

6. T2DM carbohydrate:
   Keep lower_bound=130 as a DRI adequacy floor and remove upper_bound=300, or
   remove the carbohydrate interval from formal verification?

7. Hard/safety-critical labels:
   Should hard/safety-critical mean "clinical emergency safety issue", or simply
   "prototype should reject this recommendation"? This affects HTN sodium, CKD
   sodium, CKD potassium, and CKD phosphorus labels.
```

## Recommended Conservative Revision Strategy

If the goal is a manuscript-ready but still runnable prototype, I recommend:

```text
- Keep the HTN + CKD potassium conflict case, but explicitly label CKD potassium
  2000 mg/day as an operational threshold.
- Remove or soften constraints that are not direct guideline limits.
- Avoid presenting prototype thresholds as universal clinical recommendations.
- Use "condition-aware executable guideline constraints" rather than "clinical
  prescription rules" in the manuscript.
```

