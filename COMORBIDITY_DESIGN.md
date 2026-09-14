# Step 3 design: comorbidity cluster (Iezzoni dimension 6)

Status: proposal, awaiting approval. Nothing implemented.

## Inventory

26 studies have a `harmonization_medical_history` script producing 221 distinct
columns, but the tail is very long: **182 of them appear in exactly one study.**
Only two columns reach more than eight studies.

| construct | studies | pooled viability |
|---|---|---|
| `has_diabetes` | 12 | good |
| `has_hypertension` | 8 | good |
| `has_cancer` | 7 (+ds_04 `crf_cancer`) | good |
| `number_of_chronic_conditions` | 7 | **see the count problem** |
| `has_arthritis` | 5 | usable |
| `has_history_of_heart_attack` | 5 | usable |
| `has_history_of_depression` | 5 | belongs elsewhere, see below |
| COPD, heart failure | 4 | thin |
| asthma, CHD, heart disease, PTSD, hyperlipidemia, other psychiatric | 3 | thin |
| everything else | 1-2 | not poolable |

## Full-frame screen

The inventory above comes from what the scripts produce, so all 3,605
unclustered (study, column) pairs were then screened independently with a
condition-specific vocabulary (15 condition families plus burden indices),
matching both column names and codebook labels. Results:

* The per-study scripts are **thorough**, not partial. ds_22's 19-item
  comorbidity battery (`Com_a_HaveIt`..`Com_s_HaveIt`: anaemia, arthritis,
  asthma, back pain, bowel, cancer, diabetes, hearing/vision, heart, blood
  pressure, kidney, liver, lung, mental health, nervous system, skin, ulcer,
  and two free slots) is fully harmonized into 21 columns. ds_25's battery
  becomes 24 columns, ds_23's 10 baseline flags become 9.
* The reason so few constructs reach 3+ studies is **not** missed columns: it
  is that the per-study names do not overlap. `has_anaemia_or_blood_disorder`
  exists only in ds_22, `has_dysthymia` only in ds_25. That is the tail of 182
  single-study columns.
* Only **two genuinely unharmonized sources** exist:
  1. **ds_18 `LTC_0` and `LTCsev_0`** ("LTC baseline", "LTC severity
     baseline"). ds_18 is one of four studies with no medical-history script at
     all, and the only one of those four with any comorbidity data: ds_16,
     ds_28 and ds_29 export 5-8 columns each and none is comorbidity-related.
  2. **ds_08 `ltc1`..`ltc20`**, twenty columns whose labels are only "Ltc-1"
     .. "Ltc-20" and whose values run 0-5, so they are neither yes/no flags nor
     self-describing. They need that study's codebook to interpret and are
     otherwise unusable.

**Limit of the screen.** 2,004 of 3,605 pairs (56%) carry no codebook label, so
for those only the column name can be screened. 414 of them have opaque
numbered names of exactly the `ltc1`-style that a vocabulary cannot decode.
ds_11, ds_04 and ds_26 hold most of them. A residual chance remains that an
unlabelled, opaquely-named comorbidity column exists in those studies; ruling
that out needs their codebooks read directly, which is a bounded piece of work
if you want it done before this cluster is built.

## Three source structures

1. **Per-condition flags**: ds_05 `CRF_DM`, ds_23 `DM_0`, ds_31 `DIAB`,
   ds_13 `CDI_16`, ds_22 `Com_e_HaveIt`, ds_25 named columns. Direct reads.
2. **Flags where blank means "no"**: ds_02, ds_03. This is the pattern that
   caused the live ds_03 bug, where `.map()` on a nullable dtype silently
   turned every "no" into missing. Must be handled explicitly per study.
3. **A comorbidity roster**: ds_24 carries `n_phys_comorbids` plus
   `phys_comorbid_name`, a semicolon-delimited free-text list with 253 distinct
   combinations ("Active Cancer; Diabetes; Hyperlipidemia; Hypertension"), and
   `phys_comorbid_icd9`. Conditions must be parsed out of it.

## Proposed target columns

* `has_diabetes`, `has_hypertension`, `has_cancer`, `has_arthritis`,
  `has_history_of_heart_attack` as nullable `boolean`, per
  HARMONIZATION_CONVENTIONS section 5.
* `has_heart_failure_diagnosis`, `has_chronic_obstructive_pulmonary_disease`
  at 4 studies each, emitted but documented as thin.
* `n_chronic_conditions_reported` (7 studies), **not** named
  `number_of_chronic_conditions`, for the reason below.
* `chronic_disease_score` (ds_17, ds_27), kept on its native scale.

## The count problem

`number_of_chronic_conditions` currently pools five different raw columns:

| study | column | range | what it counts |
|---|---|---|---|
| ds_03 | `CHR_CONDITIONS` | 1-6 | that study's menu |
| ds_14 | `cds2` | 0-7 | "Count of chronic conditions" per its codebook |
| ds_15 | `cds2` | **0-0** | all zeros, see below |
| ds_23 | `LTCn_0` | 1-8 | long-term conditions |
| ds_31 | `NUMDIS2` | 0-9 | "sum of all chronic diseases excluding..." |
| ds_32 | `CHRONDIS` | 0-11 | screener count |

Each study counted a different menu of conditions, so the numbers are not on a
common scale: a 3 in a study asking about six conditions is not a 3 in one
asking about eleven. This is the same shape as the instrument-scale question,
and consistent with that decision I propose **not** treating it as comparable
across studies: emit it as `n_chronic_conditions_reported`, document that it is
interpretable only within a study, and never pool it as a covariate without
that caveat.

`chronic_disease_score` stays a separate column: at 232-10,283 it is the
pharmacy-based Von Korff/Clark score, not a count, and mixing them would repeat
exactly the error this cluster is trying to avoid.

## Judgment calls needing sign-off

1. **ds_15's `cds2` is all zeros** for every patient. A count of chronic
   conditions that is uniformly zero across 65 patients is not plausible, and
   the existing pipeline currently carries it as real data. Proposal: exclude
   ds_15 from the count with a logged reason. **Worth a human glance.**
2. **`has_history_of_depression` (5 studies) is not a comorbidity here.**
   Depression is the principal diagnosis in every one of these trials, so a
   history of it is disease course, not a coexisting condition. Proposal: move
   it to the principal-diagnosis cluster rather than emit it here.
3. **No cardiac umbrella.** Heart attack (5), heart failure (4), CHD (3),
   heart disease (3) and cardiovascular disease (2) are clinically distinct and
   the studies split them differently. Proposal: emit the specific ones and do
   not invent a combined `has_cardiac_disease`, which would silently equate a
   past MI with a heart-failure diagnosis.
4. **ds_30's HbA1c is not a diabetes diagnosis.** It is a lab value, and using
   a threshold on it to infer diagnosis would be a clinical judgment this
   cluster should not make silently. Proposal: do not use it; ds_30 contributes
   no diabetes flag.
5. **ds_24/ds_25 roster parsing.** Conditions must be split out of a free-text
   list. The existing scripts already do this; re-deriving it from raw risks
   diverging from them. Proposal: re-derive, and verify the result matches the
   scripts' output exactly, the way the instruments cluster was verified.
6. **ds_05 has comorbidity data for 68 of 384 patients**; the other 316 are
   missing. Emitted as missing, not as "no".

## A note for the modelling stage, not a design question

Prevalence varies enormously by design: ds_19 is 86% diabetic and ds_08 68%,
because those trials recruited patients with diabetes or coronary heart
disease. Comorbidity here is partly an eligibility artifact rather than a
patient characteristic, which matters for any pooled model and connects to the
eligibility-criteria work currently on hold.
