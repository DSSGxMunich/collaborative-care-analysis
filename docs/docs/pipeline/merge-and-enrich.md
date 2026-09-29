# Merge, POOL2 backfill and enrichment

## Merge

`dataset.py merge` rebuilds each study from its cluster files and then stacks
all studies.

1. **Group the files by study.** Each `harmonized_datasets/*.csv` name is split
   into `(dataset_stem, cluster)`. A file whose cluster matches no current
   `harmonization_*` folder is skipped with a warning. Such files are usually
   stale; re-run `harmonize` without an ID to clear them.
2. **Validate each cluster file.** It must contain all three join keys and be
   unique on them. Duplicate keys would turn the join into a cartesian
   product, so they raise.
3. **Join the clusters** of a study with an **inner join** on
   `(STUDY_ID, patient_id, follow_up_months)`:
    - two clusters that share any non-key column raise a `ValueError`, because
      pandas would otherwise rename them silently to `_x` / `_y`,
    - lost rows trigger a prominent **ROW LOSS** warning. This means the clusters
      do not cover the same patient-visits, which is almost always a
      harmonization bug.
4. **Stack all studies** vertically. The result is the union of all columns;
   a study without a given column gets `NaN` there.
5. **Order the columns**: the join keys first, then each cluster's columns in
   alphabetical cluster order.

Output: `data/interim/merged_dataset/merged_dataset.csv`. The command also
logs how many columns each cluster contributed.

## POOL2 demographic backfill

Some studies' own files lack usable `age` or `sex`. The **POOL2** export fills
these gaps (`collaborative_care_analysis/pool2.py`). It is a pooled,
participant-level, multi-trial CSV with one row per patient.

POOL2 is deliberately **not** in `data_loading/`. It is a side input, not one
more study.

### Study ID conversion

POOL2 numbers trials with its own `Trial_ID`. The file
`data/raw/annotations/dataset_id_conversions.csv` maps `StudyNo_POOL` to
`StudyNo_OURS`. `pool_trial_id_to_study_id()` combines that mapping with the
loader file names to get `Trial_ID → STUDY_ID` (for example
`17 → 17_Katon_2001`). POOL2 trials with no counterpart in this project are
dropped.

### `pool2.load()`

- converts `Trial_ID` to `STUDY_ID`,
- uses `Original_Patient_ID` (the trial's own ID) as `patient_id`,
- harmonizes `Age` → `age` (numeric) and `Female` → `sex`. Only the labels
  `"Female"` / `"Male"` are trusted; anything else becomes missing,
- raises if the result is not unique on `(STUDY_ID, patient_id)`.

### `backfill_baseline_demographics()`

- only fills cells that are **currently missing**, never overwriting a study's
  own values,
- joins on `(STUDY_ID, patient_id)` with IDs compared as strings on both sides,
- broadcasts the time-invariant demographics to every visit of the patient,
- does nothing if the merged frame has no missing `age`/`sex`,
- logs, per column, how many values were filled and how many are still missing.

## Enrichment

`enrichment.enrich()` adds **study-arm-level characteristics** of each
collaborative-care intervention. These come from the annotation sheet
`data/raw/annotations/study_level_extra_infos.xlsx - extra_infos.csv`.

- The sheet has three header rows (category, human-readable label, machine
  name). Only the third row is used as the header.
- Bookkeeping columns (`No`, `Study ID`, `Treatment Group`, `HANNAH_*`) are
  dropped.
- The sheet's `study_id` / `treatment_id` map to `STUDY_ID` / `study_arm`, and
  **every other column is prefixed with `treatment_`**.
- The join is a **left join** on `(STUDY_ID, study_arm)`, so each patient-visit
  gets its arm's characteristics.
- The sheet only describes intervention arms. **Control arms** of studies in
  the sheet get `"no"` for every characteristic. Studies missing from the sheet
  keep `NaN`, and a warning lists them.

The enrichment raises if:

- the merged frame lacks `STUDY_ID` or `study_arm`,
- the sheet has duplicate `(study_id, treatment_id)` rows,
- a `treatment_*` column already exists in the merged frame,
- the join changes the row count.

Output: `data/interim/enriched_dataset/enriched_dataset.csv`. This is the
input for [the analysis dataset](../analysis/analysis-dataset.md) and for
most of the [tests](../testing.md).
