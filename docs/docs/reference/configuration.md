# Configuration & paths

All paths are defined in `collaborative_care_analysis/config.py` and are
relative to the repository root (`PROJ_ROOT`). Importing `config` also loads a
`.env` file if one exists, and routes loguru output through `tqdm.write`, so
log lines do not break progress bars.

## Raw inputs

| Constant                       | Path                                                                  |
|--------------------------------|-----------------------------------------------------------------------|
| `RAW_DATA_DIR`                 | `data/raw/`                                                           |
| `RAW_DATASETS_DIR`             | `data/raw/Individual Datasets/`                                       |
| `RAW_ANNOTATIONS_DIR`          | `data/raw/annotations/`                                               |
| `STUDY_LEVEL_EXTRA_INFOS_CSV`  | `data/raw/annotations/study_level_extra_infos.xlsx - extra_infos.csv` |
| `DATASET_ID_CONVERSIONS_CSV`   | `data/raw/annotations/dataset_id_conversions.csv`                     |
| `POOL2_ZIP`                    | `data/raw/260810_POOL2.zip`                                           |
| `POOL2_DIR`                    | `data/raw/260810_POOL2/`                                              |
| `POOL2_CSV`                    | `data/raw/260810_POOL2/POOL2_final.csv`                               |

## Pipeline outputs

| Constant                       | Path                                          | Written by           |
|--------------------------------|-----------------------------------------------|----------------------|
| `INTERIM_DATASETS_EXPORT_DIR`  | `data/interim/exported_datasets/`             | `export`             |
| `HARMONIZED_DATASETS_DIR`      | `data/interim/harmonized_datasets/`           | `harmonize`          |
| `MERGED_DATASET_DIR`           | `data/interim/merged_dataset/`                | `merge`              |
| `ENRICHED_DATASET_DIR`         | `data/interim/enriched_dataset/`              | `enrich` / `run`     |
| `GENERATED_CODEBOOKS_DIR`      | `data/interim/generated_codebooks/`           | `codebook`           |
| (not a constant)               | `data/interim/analysis_datasets/`             | `dataset_creation`   |

## Other directories

| Constant             | Path                   |
|----------------------|------------------------|
| `PROCESSED_DATA_DIR` | `data/processed/`      |
| `EXTERNAL_DATA_DIR`  | `data/external/`       |
| `MODELS_DIR`         | `models/`              |
| `REPORTS_DIR`        | `reports/`             |
| `FIGURES_DIR`        | `reports/figures/`     |

## Other constants and helpers

| Name                               | Where            | Value / purpose                                                     |
|------------------------------------|------------------|---------------------------------------------------------------------|
| `COLNAME_STUDYID`                  | `config.py`      | `"STUDY_ID"`                                                        |
| `normalize_study_id(value)`        | `config.py`      | NFC Unicode normalization for study IDs and file stems              |
| `CLUSTER_JOIN_KEYS`                | `dataset.py`     | `["STUDY_ID", "patient_id", "follow_up_months"]`                    |
| `TREATMENT_COL_PREFIX`             | `enrichment.py`  | `"treatment_"`, the prefix of every enrichment column               |
| `BASELINE_DEMOGRAPHIC_COLS`        | `pool2.py`       | `["age", "sex"]`, the columns backfilled from POOL2                 |
