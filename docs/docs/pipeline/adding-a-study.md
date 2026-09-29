# Adding a new study

This checklist takes a new trial from raw file to the enriched dataset.
Assume it is dataset number `34`, *Smith 2020*.

## 1. Place the raw data

```text
data/raw/Individual Datasets/34_Smith_2020/<files>
```

## 2. Inspect the file's metadata

Do not open the data in a viewer that shows rows. Use the metadata tool
instead:

```bash
uv run python -m collaborative_care_analysis.agent.inspect_metadata 34 --values
uv run python -m collaborative_care_analysis.agent.inspect_metadata 34 --stats --grep phq
```

Or generate a full codebook workbook:

```bash
uv run python -m collaborative_care_analysis.codebook 34
```

Use these to identify the ID variable, the arm variable, the time structure
(wide or long), the scales and their ranges.

## 3. Write the loader

Create `collaborative_care_analysis/data_loading/ds_34_Smith_2020.py` with a
`load()` function that:

- reads the raw file,
- renames the ID column to `patient_id`,
- reshapes to long format with `follow_up_months` (baseline = 0),
- checks uniqueness on `(patient_id, follow_up_months)`,
- ends with `.convert_dtypes()`.

See [Data loading](loading.md) for the full contract.

```bash
uv run collaborative_care_analysis/dataset.py export 34
```

## 4. Write the harmonizers

Add one script per cluster, each named `ds_34_Smith_2020.py`:

```text
harmonization_baseline/ds_34_Smith_2020.py         → age, sex, …
harmonization_medical_history/ds_34_Smith_2020.py  → comorbidities, …
harmonization_outcomes/ds_34_Smith_2020.py         → phq9_1…phq9_9, phq9_total, …
harmonization_treatment/ds_34_Smith_2020.py        → study_arm
```

Each function must return `STUDY_ID`, `patient_id`, `follow_up_months` plus
that cluster's columns. Follow the
[Harmonization conventions](../harmonization-conventions.md). Recode with
`map_with_check`.

```bash
uv run collaborative_care_analysis/dataset.py harmonize 34
```

## 5. Register the study in the annotation files

- **`study_level_extra_infos.xlsx - extra_infos.csv`**: add one row per
  intervention arm (`study_id` = `34_Smith_2020`). `tests/test_enrichment.py`
  checks that the study IDs in this sheet and the loaders match exactly.
- **`dataset_id_conversions.csv`**: if the trial is in POOL2, add its
  `StudyNo_POOL` → `StudyNo_OURS` row so that age/sex can be backfilled.

## 6. Run and test

```bash
uv run collaborative_care_analysis/dataset.py run
uv run pytest
```

Watch the logs for:

- **ROW LOSS** warnings during the merge (the clusters disagree on patient-visits),
- "dropped rows" warnings from a harmonizer,
- "No study-level extra info for …" from the enrichment step.

## 7. Update the docs

Add the study to the table in [Datasets](../datasets.md).
