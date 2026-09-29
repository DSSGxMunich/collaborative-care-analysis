# Getting started

## Prerequisites

- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — manages
  Python and all dependencies. The project pins Python `~=3.10.0`, and uv
  installs it for you.
- **R** (optional) with the packages `data.table`, `ordinal` and `splines`.
  You only need it for the [risk score model](analysis/risk-score-model.md).
- Access to the **raw trial data**. It is distributed out-of-band and is never
  committed to git.

## 1. Install

From the repository root:

```bash
uv sync
```

This creates `.venv/` and installs the runtime dependencies (pandas,
pyreadstat, typer, loguru, scikit-learn, econml, Jupyter, …) plus the dev group
(pytest, ruff, mkdocs).

## 2. Put the raw data in place

The pipeline expects this layout under `data/raw/`:

```text
data/raw/
├── Individual Datasets/
│   ├── 02_Aragones_2012/        ← one folder per trial, <NN>_<Author>_<Year>
│   ├── 03_Aragones_2019/
│   └── …
├── annotations/                 ← small annotation CSVs, these ARE in git
│   ├── dataset_id_conversions.csv
│   └── study_level_extra_infos.xlsx - extra_infos.csv
└── 260810_POOL2.zip             ← POOL2 participant-level export
```

Each loader in `collaborative_care_analysis/data_loading/` has a default path to
its trial's file(s) inside `Individual Datasets/`. See [Datasets](datasets.md)
for the full list.

Extract POOL2 once:

```bash
unzip data/raw/260810_POOL2.zip -d data/raw/260810_POOL2
```

This produces `data/raw/260810_POOL2/POOL2_final.csv`. If the file is missing,
the pipeline stops with an error that repeats this command.

!!! note "Zipped study files"
    Some trials ship their raw files as a `.zip` inside the study folder. The
    loaders for those trials extract them automatically on first use (see
    `utils.ensure_unzipped`).

## 3. Run the pipeline

```bash
uv run collaborative_care_analysis/dataset.py run
```

This runs all five stages in sequence: export, harmonize, merge, POOL2
backfill and enrich. The final output is:

```text
data/interim/enriched_dataset/enriched_dataset.csv
```

Useful variations:

```bash
uv run collaborative_care_analysis/dataset.py run 17            # only regenerate one study
uv run collaborative_care_analysis/dataset.py run -x 04 -x 17   # everything except 04 and 17
```

See the [command-line reference](pipeline/cli.md) for every command.

## 4. Check the result

```bash
uv run pytest
```

Most tests read the merged and enriched CSVs. They are **skipped** if you have
not run the pipeline yet. See [Testing](testing.md).

## 5. Build the analysis dataset

```bash
uv run python -m collaborative_care_analysis.data_analysis.dataset_creation
```

This writes the long-format and wide-format (one row per patient) datasets
used for modeling to `data/interim/analysis_datasets/`. See
[Analysis dataset](analysis/analysis-dataset.md).

## Next steps

- Read the [data privacy rules](data-privacy.md).
- Learn how the stages fit together in the [pipeline overview](pipeline/overview.md).
- Set up linting and hooks in [Development](development.md).
