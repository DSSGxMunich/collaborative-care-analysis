# Column-cluster harmonization: what was built and why

Six clusters implemented, 51 harmonized columns over 68,993 rows and 30 studies.
Every cluster works bottom-up from the concatenated raw exports, never from what
the existing per-study scripts happened to extract.

## Built

| cluster | columns | best coverage |
|---|---|---|
| age | 1 | 27 studies |
| sex | 1 | 29 studies |
| instruments | 26 | PHQ-9 15, SCL-20 10, GAD-7 8 studies |
| comorbidity | 13 | diabetes 14, cardiovascular 13, respiratory 10 studies |
| functioning | 8 | EQ-5D 5, SF summaries 3 studies |
| medication | 1 | antidepressant at entry, 4 studies |
| service use | 4 | primary care and mental health, 3 studies each |
| clinical events | 4 | death 2 studies, withdrawal 1 |
| sociodemographic | 3 | 2-3 studies |

## The rule that shaped every cluster

Pool at the level all studies can actually answer, and never invent a scale.
Three worked examples:

* **Cardiovascular.** Heart attack (6 studies), heart failure (4), angina (2),
  coronary disease (3) and undifferentiated "heart disease" (4) are each too
  thin alone. Rolled up they answer one question in 13 studies. The specific
  columns survive alongside the umbrella, so nothing is lost.
* **Depression instruments.** PHQ-9 (15 studies) and SCL-20 (10) measure the
  same construct on incompatible scales, and no study administered both, so
  there is no anchor from which to estimate a conversion. They stay separate,
  per the decision that no single model spans all 30 studies.
* **EQ-5D.** Two studies used the three-level version and two the five-level.
  A "3" means extreme problems in one and moderate in the other. Pooling raw
  levels would be a scale error, so the harmonized columns are per-dimension
  "any problem" flags, which mean the same in both versions.

## Deliberately not harmonized

Each of these could have been forced into a column. None would have meant
anything.

| construct | why not |
|---|---|
| education as a ladder | The ordinal scales are not comparable, so only the completed-secondary threshold is harmonized (4 studies). ds_13 and ds_26 have no value labels in any supplied material. |
| ethnicity | National category systems that do not map onto each other; a white/non-white binary is meaningless for the Indian cohort, and study country lives in annotations currently on hold. |

| alcohol | A diagnosis flag in one study, an AUDIT screening score in another. Different constructs. |
| income, insurance | Three studies and one study, in national currencies and national schemes. |
| hospitalisation counts | 3 studies, over different periods and for different reasons; a pooled count would mix a cardiac admission with a routine stay. |
| withdrawal reason | No study records why a patient left in a comparable form. |
| hospitalisation | 3 studies, and mostly service-use questionnaire items rather than an event flag. |
| acute clinical stability | Vitals and labs in a handful of studies only. |
| EQ-5D utility index | Three studies, three national value sets. Two indices on different tariffs are not the same quantity. |
| KCCQ | Two studies, heart-failure specific. |

## Found on the second pass

A re-scan for columns appearing in more than one study but still unclustered
turned up 44. Most are structural rather than clinical, but three are worth
recording:

* **`Cluster` (3 studies), `site` (3), `practice` (2).** Cluster-randomisation
  and site identifiers. Not a risk dimension, but they matter for any model
  that has to respect the trial design, and they are currently unused.
* **SF-36 subscale scores** (`pf_trans_score`, `mh_trans_score`, `vt_`, `sf_`,
  `rp_`, `re_`, `gh_`) in 2 studies. Standard 0-100 transformed scales and
  directly comparable, but 2 studies is below the threshold used everywhere
  else here, so they were left rather than added inconsistently.
* **`phqdep_severity`, `gad_severity`, `phqdep_total_impute`** in 2 studies
  each. Bands and imputed totals derivable from the instrument scores already
  harmonized, so superseded rather than separate variables.

## Data problems found

24 recorded in `DATA_ISSUES.csv`, four of which would have changed results:
an age variable that was a two-digit birth year, two studies with swapped
treatment arms, comorbidity flags whose blanks silently erased every negative,
and a study-name encoding issue that dropped two studies out of the data
without any error.


## Second pass: reading the study folders

A later review went back to every study folder for material not previously
opened: appendices, compiled data dictionaries, trial forms and second
codebooks. It changed four conclusions.

* **ds_08's twenty "Unklar" columns are decodable after all.** The paper cites
  Bayliss and reports "a mean of 6.2 (SD 3.0) long term conditions other than
  diabetes or heart disease". Counting `ltc1..ltc20` above zero gives 7.49, and
  6.35 once each patient's diabetes and heart-disease index conditions are
  subtracted. That reproduces the published figure and fixes the meaning of the
  columns. ds_08 now contributes a validated condition count, taking that
  column from 7 studies to 8.
* **Smoking is harmonizable.** ds_04's codebook and ds_05's compiled data
  dictionary both define their codes; with ds_25's boolean that is 3 studies.
* **Education has a defensible threshold.** ds_30's codebook defines "secondary
  or higher" as more than seven years of schooling, which fixes a boundary that
  can be applied to the US, Australian and German ladders. 4 studies.
* **A trap avoided and a real error found.** ds_24's `haheart` is not a heart
  condition but the cardiovascular-symptoms item of the SIGH-A anxiety scale.
  And its `phys_comorbid_when` is not one timing per condition, as first
  assumed, but a de-duplicated set: up to 15 conditions against at most 3
  timings, agreeing in 16% of rows. Per-condition timing is unrecoverable, so
  patients whose timings are entirely post-enrollment are excluded and the rest
  are kept with the limitation recorded.

Still open from this pass: ds_24 carries a 14-item SIGH-A anxiety scale that no
cluster harmonizes.


## Deaths and clinical override events

Built at your request, and the coverage is the headline rather than a footnote:
**death in 2 studies of 30, withdrawal in 1, cardiac events in 1.** For the
remaining 28 studies a missing follow-up still cannot be told apart from a
death, so informative censoring and competing risks stay out of reach. The
columns exist so the information that is there is not discarded, not because
the cluster can be pooled.

ds_04's deaths are confirmed against its publication: the paper reports 10
deaths on CASA and 13 on usual care, and a death time is recorded for exactly
those 23 patients. ds_09 adjudicates all-cause mortality separately and has 1.

Two false leads were removed. ds_11's `death_t` and `phq2wk_dead_di_t` are
labelled "Thought-of-death" and "Thoughts that you would be better off dead":
they are the PHQ-9 suicidality item, not vital status, and ds_11 had been
counted as a death study on the strength of the column name. ds_32's
`cesd_item_thought_about_death` is the same item in the CES-D.
