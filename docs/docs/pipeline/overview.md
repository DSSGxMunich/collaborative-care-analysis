# Pipeline overview

The data pipeline lives in `collaborative_care_analysis/dataset.py`, a
[Typer](https://typer.tiangolo.com/) CLI. It turns about 30 heterogeneous trial
files into a single harmonized patient-visit dataset.

## Stages

| # | Stage             | Command     | Input                                   | Output (under `data/interim/`)                           |
|---|-------------------|-------------|-----------------------------------------|----------------------------------------------------------|
| 1 | Export            | `export`    | raw trial files                         | `exported_datasets/ds_<NN>_<Name>.csv`                   |
| 2 | Harmonize         | `harmonize` | loader output (re-loaded, not the CSV)  | `harmonized_datasets/ds_<NN>_<Name>_<cluster>.csv`       |
| 3 | Merge             | `merge`     | harmonized cluster CSVs                 | `merged_dataset/merged_dataset.csv`                      |
| 4 | POOL2 backfill    | `enrich`    | merged frame + POOL2 CSV                | (in memory)                                              |
| 5 | Enrich            | `enrich`    | backfilled frame + extra-info sheet     | `enriched_dataset/enriched_dataset.csv`                  |

`run` executes all five stages in order. `enrich` runs stages 4 and 5 on an
existing merged dataset.

```text
data_loading/ds_NN_*.py : load()  ──►  exported_datasets/            (stage 1, for inspection)
        │
        └─► + STUDY_ID column
              │
              ├─► harmonization_baseline/ds_NN_*.py        ─┐
              ├─► harmonization_medical_history/ds_NN_*.py  │  one CSV per
              ├─► harmonization_outcomes/ds_NN_*.py         │  (study, cluster)
              └─► harmonization_treatment/ds_NN_*.py       ─┘
                                                            │
      per study: inner-join clusters on (STUDY_ID, patient_id, follow_up_months)
      all studies: stack vertically (union of columns, gaps = NaN)
                                                            │
                                                  merged_dataset.csv
                                                            │
                         fill missing age / sex from POOL2 (per patient)
                                                            │
             left-join study-arm characteristics on (STUDY_ID, study_arm)
                                                            │
                                                  enriched_dataset.csv
```

## Key identifiers

| Column             | Meaning                                                                                       |
|--------------------|-----------------------------------------------------------------------------------------------|
| `STUDY_ID`         | Study identifier from the loader file name: `ds_17_Katon_2001.py` → `17_Katon_2001`. Added automatically before harmonization. |
| `patient_id`       | The trial's own participant identifier. The loader renames it to `patient_id`.                |
| `follow_up_months` | Months since baseline. Baseline is `0`.                                                       |
| `study_arm`        | `"control"` or `"intervention"`, set by the treatment harmonizer.                             |

`(STUDY_ID, patient_id, follow_up_months)` uniquely identifies a row. It is the
join key between clusters.

## Design principles

- **Long format everywhere.** Each loader reshapes repeated measurements to one
  row per visit, so every downstream step sees the same structure.
- **Fail loudly.** Unmapped codes, duplicate join keys, missing key columns,
  column-name collisions between clusters and row-count changes during
  enrichment all raise. Row loss during the join logs a prominent warning.
- **Clean regeneration.** A run without a dataset ID (including an `--exclude`
  run) deletes the old CSVs in each output directory first. Renamed, deleted
  or excluded studies therefore cannot leave stale files behind. A targeted
  run (`run 17`) only overwrites that study's files.
- **Convention-based discovery.** Loaders and harmonizers are discovered by
  file and folder name. No registry needs updating. See
  [Harmonization](harmonization.md).
- **Unicode-safe study IDs.** Two study names contain umlauts (Hölzel,
  Unützer). Every study ID is normalized to NFC with
  `config.normalize_study_id`, so macOS-decomposed file names still match.

## Next

- [Command-line reference](cli.md)
- [Data loading](loading.md)
- [Harmonization](harmonization.md)
- [Merge, POOL2 backfill and enrichment](merge-and-enrich.md)
