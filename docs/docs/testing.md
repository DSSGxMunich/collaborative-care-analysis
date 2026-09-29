# Testing & quality checks

```bash
uv run pytest
uv run pytest tests/test_pool2.py -v     # a single file
```

## How the tests get data

The tests work on **real pipeline outputs**, not on committed fixtures, since
no data may be committed. `tests/conftest.py` provides these fixtures:

| Fixture          | Reads                                                     | If missing          |
|------------------|-----------------------------------------------------------|---------------------|
| `merged_df`      | `data/interim/merged_dataset/merged_dataset.csv`          | test is **skipped** |
| `enriched_df`    | `data/interim/enriched_dataset/enriched_dataset.csv`      | test is **skipped** |
| `treatment_cols` | the `treatment_*` columns of `enriched_df`                |                     |

Run the pipeline (`dataset.py run`) before testing. A green run on a machine
without data only means that everything was skipped.

Some tests call the loaders directly (they are parametrized over every
`data_loading/ds_*.py`). Those need the raw data.

Assertion messages report **counts and column names**, never patient values.

## What is tested

| File                              | Checks                                                                                           |
|-----------------------------------|--------------------------------------------------------------------------------------------------|
| `test_column_hygiene.py`          | No duplicate column names, no two columns with identical content, no fully empty columns, no constant columns |
| `test_depression_instruments.py`  | PHQ-9 items 0–3 and total 0–27, integer-valued; total = sum of items; complete items imply a total; GAD-7, K10, HRSD-17, HSCL, CIS-R and PROMIS ranges; suicidality fields take a small closed set of codes |
| `test_follow_up.py`               | `follow_up_months` is numeric, non-negative, uses one consistent baseline value, and stays within a plausible maximum |
| `test_loader_dtypes.py`           | Every loader returns pandas nullable dtypes, and no column mixes Python value types              |
| `test_patient_identity.py`        | `patient_id` is never missing; `(STUDY_ID, patient_id, follow_up_months)` is unique; one `study_arm` and one `sex` per patient; loaders that report age/sex have no gaps; `sex` is a category and `age` is in range |
| `test_enrichment.py`              | The study IDs in the extra-info sheet match the loaders exactly                                  |
| `test_pool2.py`                   | Every POOL2 trial ID maps to a real loader; `load()` is one row per patient with harmonized age/sex; a missing export raises with the unzip command; backfill fills only missing cells and does nothing when nothing is missing |

`tests/helpers.py` has shared utilities: `present()`, `assert_in_range()`,
`find_non_integer_rows()`, and loader discovery and import.

## Checks built into the pipeline

Many problems are caught when the pipeline runs, before any test:

- `map_with_check` fails on unmapped codes,
- harmonizer output is checked for `None` and a missing `STUDY_ID`, and row
  drops trigger a warning,
- the merge fails on missing or duplicate join keys and on column collisions,
  and warns on row loss,
- POOL2 loading fails if it is not unique per patient,
- enrichment fails on a non-unique sheet, column collisions or a row-count
  change.
