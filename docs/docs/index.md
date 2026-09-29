# Collaborative Care Analysis

**Depression Treatment Navigator for Primary Care** — DSSGx Munich 2026.

This project pools individual participant data (IPD) from about 30 randomized
trials of **collaborative care** for depression in primary care. It puts every
trial into one common format and uses the pooled data to model which patients
benefit most from which components of collaborative care.

## What the repository does

1. **Loads** each trial's raw SPSS / Stata / CSV / Excel files into a tidy,
   long-format table (one row per patient per visit).
2. **Harmonizes** each trial into shared variable *clusters* (baseline
   demographics, medical history, outcomes, treatment arm) with common column
   names and codings.
3. **Merges** all trials into one patient-visit dataset.
4. **Enriches** it with baseline age / sex from the POOL2 export and with
   study-arm-level descriptions of each collaborative-care intervention.
5. **Analyses** the result:
    - **Step 1**: a prognostic risk score for 12-month PHQ-9, from a
      proportional-odds mixed model in R.
    - **Step 2**: a component network meta-analysis (CNMA) that lets each
      intervention component's effect vary with that risk score.

```text
raw trial files ──► load ──► harmonize ──► merge ──► POOL2 backfill ──► enrich
 data/raw/           │          │            │                          │
                 exported   harmonized    merged                   enriched_dataset.csv
                                                                          │
                                           analysis dataset (baseline + 12 months)
                                                    │                 │
                                           Step 1 risk score ──► Step 2 CNMA
```

## Where to start

| If you want to…                              | Read                                                   |
|----------------------------------------------|--------------------------------------------------------|
| Set up the project and run the pipeline      | [Getting started](getting-started.md)                  |
| Know what you may and may not do with the data | [Data privacy rules](data-privacy.md)               |
| Understand how the pipeline works            | [Pipeline overview](pipeline/overview.md)              |
| Look up a command                            | [Command-line reference](pipeline/cli.md)              |
| Add or fix a study                           | [Adding a new study](pipeline/adding-a-study.md)       |
| See which trials are included                | [Datasets](datasets.md)                                |
| Name and code harmonized variables           | [Harmonization conventions](harmonization-conventions.md) |
| Work on the statistical models               | [Analysis](analysis/analysis-dataset.md)               |

!!! warning "Sensitive data"
    The raw data are confidential trial data. None of it is committed to git,
    and no one (human or AI agent) may print individual records. Read
    [Data privacy rules](data-privacy.md) before you work with the data.

## Building these docs

The documentation is a plain [MkDocs](https://www.mkdocs.org/) site that builds
and renders fully offline. From the repository root:

```bash
uv sync                                        # installs mkdocs (dev dependency)
uv run mkdocs serve -f docs/mkdocs.yml         # live preview at http://127.0.0.1:8000
uv run mkdocs build -f docs/mkdocs.yml         # static site in docs/site/
```

The built site in `docs/site/` is git-ignored. You can open
`docs/site/index.html` directly in a browser.
