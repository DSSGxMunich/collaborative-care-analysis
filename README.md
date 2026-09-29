# Collaborative Care Analysis

Depression Treatment Navigator for Primary Care

This repository contains the code and documentation for the project "Collaborative Care Compass", developed during the Data Science for Social Good (DSSG) Summer Fellowship Munich 2026.

## Project Overview 🌍

The project aims to optimise the implementation of Collaborative Care for Depression in German primary care by identifying the most effective combinations of intervention components for specific patient profiles. Leveraging a dataset from the LMU University Hospital, the team analyses how individual treatment elements impact outcomes, to support the effective use of resources and improve patient recovery. The ultimate goal is an intuitive, patient-focused prediction tool, designed in collaboration with general practitioners, that provides data-driven decision support that is both clinically effective and practically sustainable.

## Background and Problem Statement 🎯

Collaborative care, in which the general practitioner works with a care manager and a mental health specialist, is an established approach to treating depression in primary care. But trials combine different components, patients benefit to different degrees, and each trial recorded its data differently. To learn which components work, and for whom, the trials must first be brought into one consistent, pooled dataset.

## Project Goal and Contributions 🚀

The goal of this project is to support personalized collaborative care for depression in German general practice. We contribute in the following ways:

- **Harmonized pooled dataset:** a reproducible pipeline that exports, harmonizes, merges and enriches participant-level data from multiple collaborative care RCTs into one analysis-ready dataset.
- **Clinical prediction model:** a component network meta-analysis (CNMA) and risk-score modelling on the pooled data, to estimate how collaborative care components affect outcomes for different patients.
- **Web prototype:** a prototype tool showing how these insights could be brought into general practice.
- **Documentation:** technical documentation of the data pipeline, modelling approach and suggestions for future work.

## Documentation

The full technical documentation is an MkDocs site in `docs/`. Preview it locally with:

```bash
uv run mkdocs serve -f docs/mkdocs.yml
```

Then open http://127.0.0.1:8000.

## Exporting Datasets

Export datasets to the interim data directory by running the following command. You can optionally specify a dataset id to export a specific dataset. If no dataset id is specified, all datasets will be exported.

```bash
uv run collaborative_care_analysis/dataset.py export

uv run collaborative_care_analysis/dataset.py export 04

uv run collaborative_care_analysis/dataset.py export Bekelman_2018
```

## Harmonizing Datasets

Harmonize datasets by running the following command. This will load each dataset and apply any harmonization scripts found in `harmonization_*` folders, saving the results to the interim harmonized datasets directory. You can optionally specify a dataset id to harmonize a specific dataset.

```bash
uv run collaborative_care_analysis/dataset.py harmonize

uv run collaborative_care_analysis/dataset.py harmonize 17

uv run collaborative_care_analysis/dataset.py harmonize Katon_2001
```

## Merging Harmonized Datasets

Join each study's harmonized clusters, then stack all studies into one dataset.

```bash
uv run collaborative_care_analysis/dataset.py merge
```

Clusters are joined on `STUDY_ID`, `patient_id`, and `follow_up_months` (inner join), then concatenated vertically. Columns missing from a study are filled with `NaN`. The command also returns a mapping of cluster name to the columns it contributed across all studies.

The merge raises on a missing join key, duplicate keys, or a column name claimed by two clusters, and warns loudly if the join drops rows.

## Running the Full Pipeline

```bash
uv run collaborative_care_analysis/dataset.py run

uv run collaborative_care_analysis/dataset.py run 4

uv run collaborative_care_analysis/dataset.py run Katon_2001
```

Runs `export`, `harmonize`, and `merge` in sequence, then backfills missing
baseline `age` / `sex` from the POOL2 export and applies study-level `enrich`ment.

## POOL2 Demographic Backfill

Some studies' own data does not carry a usable `age` or `sex`. The `enrich` and
`run` commands fill those gaps from the POOL2 participant-level export, joining
on study and patient id.

POOL2 ships as a zip that must be extracted once before running the pipeline:

```bash
unzip data/raw/260810_POOL2.zip -d data/raw/260810_POOL2
```

This produces `data/raw/260810_POOL2/POOL2_final.csv` (and `POOL2_final_NEU.csv`).
If the CSV is missing, the pipeline stops with an error repeating this command.

POOL2 numbers studies with its own `Trial_ID`; `data/raw/annotations/dataset_id_conversions.csv`
maps that to this project's dataset numbering.

## Run While Excluding Some Datasets

Use `--exclude` to run the full pipeline while excluding a dataset:

```bash
uv run collaborative_care_analysis/dataset.py run --exclude 04
```

The shorter `-x` option does the same thing:

```bash
uv run collaborative_care_analysis/dataset.py run -x 04
```

Repeat either option to exclude multiple datasets:

```bash
uv run collaborative_care_analysis/dataset.py run -x 04 -x 17
```

Alternatively:

```bash
uv run collaborative_care_analysis/dataset.py run --exclude 04 --exclude 17
```

An exclusion run regenerates the exported, harmonized, merged, and enriched datasets without the excluded datasets. Raw datasets are not modified.

After the pipeline completes successfully, a bold red warning lists the excluded dataset identifiers.


## Generating Codebooks

If a dataset does not include a codebook, generate one from the metadata embedded in its SPSS or Stata files by specifying the numeric dataset ID: 

```bash
uv run python -m collaborative_care_analysis.codebook 13
```

Generated codebooks are saved under `data/interim/generated_codebooks/`. Each Excel workbook contains three sheets: `Dataset Metadata`, `Variable Labels`, and `Value Labels`.

## Project Organization

```
├── LICENSE            <- Open-source license if one is chosen
├── AGENTS.md          <- Data privacy rules for AI coding agents.
├── README.md          <- The top-level README for developers using this project.
├── data
│   ├── external       <- Data from third party sources.
│   ├── interim        <- Intermediate data that has been transformed.
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── docs               <- A default mkdocs project; see www.mkdocs.org for details
│
├── models             <- Trained and serialized models, model predictions, or model summaries
│
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
│
├── pyproject.toml     <- Project configuration file with package metadata for 
│                         collaborative_care_analysis and configuration for tools like black
│
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
│
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── setup.cfg          <- Configuration file for flake8
│
└── collaborative_care_analysis   <- Source code for use in this project.
    │
    ├── __init__.py             <- Makes collaborative_care_analysis a Python module
    │
    ├── config.py               <- Store useful variables and configuration
    │
    ├── dataset.py              <- Scripts to download or generate data
    │
    ├── codebook.py             <- Generate codebooks from embedded SPSS and Stata metadata
    │
    ├── features.py             <- Code to create features for modeling
    │
    ├── modeling                
    │   ├── __init__.py 
    │   ├── predict.py          <- Code to run model inference with trained models          
    │   └── train.py            <- Code to train models
    │
    └── plots.py                <- Code to create visualizations
```

--------

## Development

### Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not already available, then create the project environment and install its dependencies:

```bash
uv sync
```

### Linting and Formatting

Run the following command to check the code and apply formatting fixes:

```bash
uv run ruff check . --fix && uv run ruff format
```

### Tests

Run the test suite with:

```bash
uv run pytest
```

### Pre-commit Hooks (optional)

Register the repository hooks to run checks automatically before each commit:

```bash
uvx pre-commit install
```

This will automatically run checks, such as the linter and tests, before each commit. If any of the checks fail, the commit will be aborted.

### Stripping Notebook Outputs

This repo uses [nbstripout](https://github.com/kynan/nbstripout) to keep notebook outputs out of git history. Install it once per clone:

```bash
uv add nbstripout
nbstripout --install
```

This registers a git filter that strips outputs from notebooks when they're staged for commit. Your local `.ipynb` files on disk keep their outputs — only what gets committed is stripped.

Verify it's active with:

```bash
uv run nbstripout --status
```