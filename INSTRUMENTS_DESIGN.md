# Step 3 design: measurement instruments cluster (depression / anxiety core)

Status: **implemented** on `ai/cluster-instruments` (uncommitted). Approved
2026-09-13. Verified against the existing per-study pipeline: 30,562 PHQ-9
rows, 21,908 GAD-7 rows and 14,143 SCL-20 rows compared, **0 disagreements**.

## Scope

This cluster covers the repeated **depression and anxiety** instruments:
PHQ-9, GAD-7, SCL-20, and the five single-study instruments. EQ-5D, SF-12/36,
KCCQ and WHODAS are deferred to the health-status/quality-of-life cluster,
which derives from them. Flagged as a scope decision, not a silent omission.

Settled beforehand: instruments keep their native scales, no cross-walk, no
within-study standardisation.

## Target columns

| column | type | range | notes |
|---|---|---|---|
| `phq9_1` .. `phq9_9` | Int64 | 0-3 | item scores |
| `phq9_total` | Int64 | 0-27 | sum of the nine items |
| `phq9_difficulty` | Int64 | 0-3 | the 10th "difficulty" item, **never in the total** |
| `gad7_1` .. `gad7_7` | Int64 | 0-3 | |
| `gad7_total` | Int64 | 0-21 | |
| `gad7_difficulty` | Int64 | 0-3 | ds_04's `gad08` |
| `scl20_mean` | Float64 | 0-4 | mean of 20 SCL-90 depression items |
| `hscl_total` | Float64 | | ds_03 only |
| `bdi_total` | Int64 | 0-63 | ds_09 only |
| `cisr_total` | Int64 | | ds_20 only |
| `hrsd17_total` | Int64 | 0-52 | ds_23 only |
| `cesd23_total` | Int64 | | ds_32 only, 23-item variant |

## Verified per-study sources

**PHQ-9 total, 15 studies.** Every source range-checked inside 0-27.

| study | raw column | evidence |
|---|---|---|
| ds_02, ds_21, ds_22, ds_24, ds_25, ds_26 | `phq9_total` | loader already normalised the name |
| ds_04 | `phqtotalv2` | equals sum of `phq01..phq09` on all 982 rows |
| ds_05 | `PHQSCORE` | |
| ds_10 | `phqdep_total` | items present as `phq2wk_*` content names |
| ds_13 | `PHQ_Summe` | items `PHQ9_1..9`, German text labels mapped 0-3 |
| ds_30 | `depression` | equals sum of `phq1..phq9` on all 7,680 rows |
| ds_33 | `Depression_severity` | study's own `DepresSev_Mes` field reads `HPQ9`, i.e. PHQ-9 with the typo the loader audit flagged |
| ds_08, ds_11, ds_12 | computed from items | no shipped total |

**GAD-7 total, 9 studies:** ds_04 `gadtotal` (= sum of `gad01..gad07`, all 1,002
rows), ds_10 `gad_total`, ds_11 `gad_total`, ds_22/ds_26 `gad7_total`,
ds_30 `anxiety` (= sum of `gad1..gad7`, all 7,680 rows), and ds_05/ds_08/ds_13
computed from items.

**SCL-20 mean, 10 studies:** ds_14, 15, 16, 17, 18, 19, 27, 28, 31 and
**ds_29**, which has `scl20_mean` in its export but no outcomes script, so it is
absent from the merged dataset today. All ten range-check inside 0-4.
Construct confirmed in ds_14's loader: "the average of the scores for 20
depression items in the SCL-90 (each item scores from 0 to 4)".

## Scoring rules

1. Where a study ships a total **and** items, use the shipped total, after
   verifying it equals the item sum. Verified for ds_04, ds_30.
2. Where no total ships, compute it, requiring **all** items present
   (`min_count=9`), following `harmonization_outcomes/ds_13`. A partial item
   set yields NA, never a silently low score.
3. The difficulty item is never added to the total.
4. Item scores are mapped through `map_with_check`, so an unexpected code fails
   loudly rather than becoming NA.

## Judgment calls needing sign-off

1. **ds_04 `phqtotal` vs `phqtotalv2`.** v2 matches the item sum exactly on all
   982 rows; `phqtotal` disagrees on 3 rows and covers 21 extra rows scored from
   incomplete items. Proposal: use v2, mark `phqtotal` superseded, accept the
   loss of 21 partial-item rows. The existing script already chose v2.
2. **ds_10 `gad_total` vs `gad_total_impute`.** The imputed variant adds 7 rows
   and never disagrees elsewhere. Proposal: use the non-imputed `gad_total` and
   record why, rather than let imputed values enter a harmonized column
   unlabelled.
3. **ds_33 `ZDepression_severity`** is a pre-computed within-study z-score
   (mean 0, sd 0.999). Proposal: mark superseded and never use it, consistent
   with the no-standardisation decision.
4. **Scope**: EQ-5D / SF-12 / SF-36 / KCCQ / WHODAS deferred to the QoL cluster.
5. **ds_08's continuous `follow_up_months`** (2.9-16.2) means its PHQ-9 and
   GAD-7 series cannot be placed on a fixed visit grid. Storage is lossless;
   any later visit-alignment logic must handle it.


## What implementation changed versus this design

Four things surfaced only once the code ran against all 30 studies.

1. **ds_22's GAD-7 is on an unresolved scale and is excluded.** Its
   `gad7_total` is an integer 0-26, and 211 of 1,822 values exceed 21, the
   most a GAD-7 can score. The excess appears at every wave including
   baseline, so it is not an artifact of the loader stacking the 36-month
   wave. The study ships no GAD-7 items and its codebook says only
   "Generalised Anxiety Disorder Total score", so the scale cannot be
   recovered from the data. Pooling it would put two scales in one column.
   Its PHQ-9 is unaffected and is used. **Needs a human decision.**
2. **ds_11 records its PHQ-9 on two different forms.** The `_t` toolkit
   columns hold baseline (1,868 rows) and the unsuffixed ones hold the 3- and
   12-month waves (2,361 rows); neither set alone covers the study. Both are
   now read, which recovered exactly the 2,361 rows the first implementation
   was missing.
3. **A whole-number guard was added.** ds_26 ships 2 non-integer PHQ-9 totals
   and 31 non-integer GAD-7 totals, and no items to recompute from. A sum of
   integer items cannot be fractional, so these are set missing with a warning.
4. **ds_13 has 2 items coded 9** in `GAD7_1`, outside the 0-3 response range.
   Set missing by the range guard.

## Coverage achieved

| column | studies | rows |
|---|---|---|
| `phq9_total` | 15 | 30,563 |
| `gad7_total` | 8 | 21,912 |
| `scl20_mean` | **10** | 14,548 |
| `phq9_1`..`phq9_9` | up to 10 | |
| `phq9_difficulty` | 3 | 9,840 |
| `hscl_total`, `bdi_total`, `cisr_total`, `hrsd17_total`, `cesd23_total` | 1 each | |

ds_29 reaches the pooled data for the first time: it has `scl20_mean` in its
export but no harmonization script, so it is absent from the merged dataset.
