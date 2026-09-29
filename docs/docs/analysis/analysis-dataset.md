# Analysis dataset

`collaborative_care_analysis/data_analysis/dataset_creation.py` turns the
enriched patient-visit dataset into the modeling cohort. The cohort contains
patients with a baseline PHQ-9 and a PHQ-9 at about **12 months**.

```bash
uv run python -m collaborative_care_analysis.data_analysis.dataset_creation
```

| Function        | Output                                                          | Shape                                          |
|-----------------|-----------------------------------------------------------------|------------------------------------------------|
| `create_long()` | `data/interim/analysis_datasets/analysis_dataset.csv`           | 2 rows per patient (baseline + 12 months)      |
| `create_wide()` | `data/interim/analysis_datasets/analysis_dataset_wide.csv`      | 1 row per patient: baseline predictors, `baseline_phq9`, outcome `phq9_12mo` |

Both functions accept `save=False` to return the frame without writing it.

## Filtering steps

The shared `_clean()` function applies these steps in order. After each step it
logs the **shape** (row and column counts only):

| # | Step                                                                                         | Level    |
|---|----------------------------------------------------------------------------------------------|----------|
| 1 | Keep rows with an integer-valued `phq9_total`, and cast it to `int32`                        | row      |
| 2 | Drop studies with no `phq9_total` at all                                                     | study    |
| 3 | Keep patients with a baseline row (`follow_up_months == 0`)                                  | patient  |
| 4 | Keep patients with a row in the **11.5–12.5 month** window                                   | patient  |
| 5 | Keep only baseline rows and 11.5–12.5-month rows                                             | row      |
| 6 | Broadcast `age` within each patient, then drop patients with no age                          | patient  |
| 7 | Broadcast `sex` within each patient, drop patients with no sex, and cast to `category`       | patient  |
| 8 | Broadcast `study_arm` within each patient, then drop patients with a missing arm             | patient  |
| 9 | Drop patients with a missing **baseline `gad7_total`**                                       | patient  |
| 10| Drop patients with `sex == "Other"`                                                          | patient  |

"Broadcast" means filling a time-invariant value forwards and backwards
across a patient's own rows. Patient-level filters remove **all** rows of
the patient.

!!! note "Attrition audit"
    `notebooks/01_filter_datasets.ipynb` repeats the same filters with one
    operation per cell. It reports how many rows, patients and studies each
    filter removes, together with a study survival matrix. The baseline GAD-7
    filter (step 9) removes the most studies: 13 studies remain before it and
    9 after it.

## Wide format

`create_wide()` splits the long frame into:

- **baseline**: all columns from the `follow_up_months == 0` row, with
  `phq9_total` renamed to `baseline_phq9`,
- **outcome**: `phq9_total` from the 11.5–12.5-month row, renamed to `phq9_12mo`,

and inner-joins them on `(STUDY_ID, patient_id)`. The earlier filters should
make the join lossless. If it drops patients anyway, it logs a warning.
