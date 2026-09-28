# Collaborative Care Analysis

Depression Treatment Navigator for Primary Care — the analysis code behind a
DSSGx Munich 2026 project.

Collaborative care for depression bundles several components (for example case
management, specialist involvement or a relapse-prevention plan). This
repository pools individual patient data (IPD) from randomised controlled trials
of collaborative care and estimates how a patient's PHQ-9 score after 12 months
is likely to develop under usual care and under different care components.

The results feed a research prototype web app for GPs and patients:

- App: <https://dssgxmunich.github.io/collaborative-care-webapp/>
- App code: <https://github.com/DSSGxMunich/collaborative-care-webapp>

> **Research prototype.** The model has not been clinically validated and does
> not replace clinical judgement.

## How it works

The work runs in two parts: a data pipeline that turns the raw trial files into
one harmonised dataset, and a two-step model fitted on that dataset.

```
raw trial files ─► export ─► harmonize ─► merge ─► enrich ─► analysis dataset
                                                                  │
                                    Step 1: risk score (R, clmm) ◄┘
                                                  │
                                    Step 2: CNMA (Python, PyMC)
```

1. **Data pipeline** (`collaborative_care_analysis/dataset.py`): loads each
   trial's SPSS/Stata/CSV files, harmonises them to shared column names,
   merges all studies into one patient-visit table and adds study-level
   information about each arm's care components.
2. **Analysis dataset** (`collaborative_care_analysis/data_analysis/dataset_creation.py`):
   keeps patients with a baseline and a ~12-month PHQ-9 (11.5–12.5 months) and
   known age and sex.
3. **Step 1 – risk score** (`collaborative_care_analysis/data_analysis/risk_score_model.R`):
   a proportional-odds mixed model (`ordinal::clmm`, random effects per study)
   predicts the 12-month PHQ-9 under usual care from baseline PHQ-9, age and sex.
4. **Step 2 – component network meta-analysis** (`notebooks/02_CNMA_version1.ipynb`):
   a Bayesian model (PyMC) splits the treatment effect into care components and
   lets each effect vary with the Step-1 risk score.

## Data access

The trial data is **not** part of this repository and is only available to
approved project members. Put the raw files under `data/raw/` (see
[Project organisation](#project-organisation)).

Before working with the data, read [AGENTS.md](AGENTS.md). In short: never
print, log or commit row-level data — only schema information and aggregates.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
uv sync
```

Step 1 also needs R with the packages `ordinal`, `data.table` and `splines`.

## Data pipeline

### Run everything

```bash
uv run collaborative_care_analysis/dataset.py run
```

This runs `export`, `harmonize` and `merge`, backfills missing baseline `age` /
`sex` from POOL2 and adds the study-level information (`enrich`). You can limit
it to one dataset by id or name:

```bash
uv run collaborative_care_analysis/dataset.py run 4
uv run collaborative_care_analysis/dataset.py run Katon_2001
```

### Individual steps

```bash
# 1. Export raw datasets to data/interim/exported_datasets/
uv run collaborative_care_analysis/dataset.py export [DATASET]

# 2. Apply the harmonization_* scripts
uv run collaborative_care_analysis/dataset.py harmonize [DATASET]

# 3. Join each study's clusters, then stack all studies
uv run collaborative_care_analysis/dataset.py merge

# 4. Add study-level arm information
uv run collaborative_care_analysis/dataset.py enrich
```

`merge` joins clusters on `STUDY_ID`, `patient_id` and `follow_up_months`
(inner join) and fills columns a study doesn't have with `NaN`. It stops on a
missing join key, duplicate keys or a column claimed by two clusters, and warns
if the join drops rows.

### Excluding datasets

```bash
uv run collaborative_care_analysis/dataset.py run -x 04 -x 17
```

`--exclude` / `-x` can be repeated. The excluded ids are listed in a red warning
at the end. Raw data is never modified.

### POOL2 demographic backfill

Some studies don't carry a usable `age` or `sex`. The pipeline fills these from
the POOL2 participant-level export, which must be extracted once:

```bash
unzip data/raw/260810_POOL2.zip -d data/raw/260810_POOL2
```

`data/raw/annotations/dataset_id_conversions.csv` maps POOL2's `Trial_ID` to
this project's dataset numbers.

## Analysis

```bash
# Build the long and wide analysis datasets in data/interim/analysis_datasets/
uv run python -m collaborative_care_analysis.data_analysis.dataset_creation

# Step 1: fit the risk-score model, saved to models/risk_score_model.rds
Rscript collaborative_care_analysis/data_analysis/risk_score_model.R fit
```

Step 2 lives in `notebooks/02_CNMA_version1.ipynb`. It reads the Step-1 risk
scores from `data/processed/risk_scores.csv` and exports the CNMA coefficients
and posterior draws.

`notebooks/01_filter_datasets.ipynb` walks through the cohort filtering one step
at a time and shows how many rows, patients and studies each filter removes.

## Inspecting data safely

To look at a dataset's schema without reading any participant rows:

```bash
uv run python -m collaborative_care_analysis.agent.inspect_metadata 16
uv run python -m collaborative_care_analysis.agent.inspect_metadata 16 --grep scl --stats
```

To generate a codebook (Excel) from the metadata embedded in SPSS/Stata files:

```bash
uv run python -m collaborative_care_analysis.codebook 13
```

Codebooks are saved to `data/interim/generated_codebooks/`.

## Project organisation

```
├── AGENTS.md                     <- Data privacy rules (read before touching data)
├── HARMONIZATION_CONVENTIONS.md  <- Column naming and coding rules for harmonisation
├── data
│   ├── raw                       <- Original trial files, annotations, POOL2 (not in git)
│   ├── interim                   <- Exported, harmonised, merged, enriched and analysis datasets
│   └── processed                 <- Final model inputs, e.g. risk scores
├── docs                          <- mkdocs project
├── models                        <- Fitted models, e.g. risk_score_model.rds
├── notebooks                     <- Cohort filtering and CNMA notebooks
├── reports/figures               <- Generated figures
├── tests                         <- pytest suite
└── collaborative_care_analysis   <- Source code
    ├── dataset.py                <- Pipeline CLI: export, harmonize, merge, enrich, run
    ├── data_loading/             <- One loader per trial (ds_<id>_<Author>_<Year>.py)
    ├── harmonization_baseline/   <- Harmonisation scripts, one folder per cluster
    ├── harmonization_medical_history/
    ├── harmonization_outcomes/
    ├── harmonization_treatment/
    ├── enrichment.py             <- Adds study-level arm information
    ├── pool2.py                  <- Loads POOL2 for the demographic backfill
    ├── data_analysis/
    │   ├── dataset_creation.py   <- Builds the analysis datasets
    │   └── risk_score_model.R    <- Step 1 risk-score model
    ├── agent/inspect_metadata.py <- Privacy-safe schema inspection
    ├── codebook.py               <- Codebook generation
    ├── config.py                 <- Paths and shared constants
    └── utils.py
```

## Adding a new trial

1. Add a loader `collaborative_care_analysis/data_loading/ds_<id>_<Author>_<Year>.py`.
2. Add a matching script (same file name) in each `harmonization_*` folder,
   following [HARMONIZATION_CONVENTIONS.md](HARMONIZATION_CONVENTIONS.md).
3. Add the study's arms to the study-level annotations sheet.
4. Run `uv run collaborative_care_analysis/dataset.py run <id>` and check the
   merge warnings.

## Development

```bash
uv run ruff check . --fix && uv run ruff format   # lint and format
uv run pytest                                     # tests
uvx pre-commit install                            # optional pre-commit hooks
```

CI runs `ruff check` and `ruff format --check` on pull requests to `main`.

Notebook outputs must not be committed (they could contain data). Install
[nbstripout](https://github.com/kynan/nbstripout) once per clone:

```bash
uv add nbstripout
nbstripout --install
uv run nbstripout --status   # check it is active
```

## Team

DSSGx Munich 2026 fellows: Amina Džafić, Boaz Kafuti, Loiruck Godwin,
Xiaohan Wu, Alexander Richard.
