# Collaborative Care Compass 🧭

![Python](https://img.shields.io/badge/python-3.10-blue) ![uv](https://img.shields.io/badge/managed%20with-uv-purple) ![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

This repository contains the code and documentation for the project "Collaborative Care Compass", developed during the [Data Science for Social Good (DSSG) Summer Fellowship Munich 2026](https://www.dssgxmunich.org/call-for-fellows).

## Project Overview 🌍
 
The project aims to optimise the implementation of Collaborative Care for Depression in German primary care by identifying the most effective combinations of intervention components for specific patient profiles. Leveraging a dataset from the LMU University Hospital, the team analyses how individual treatment elements affect outcomes, to support the effective use of resources and improve patient recovery. The ultimate goal is an intuitive, patient-focused prediction tool, designed in collaboration with general practitioners, that provides data-driven decision support that is both clinically effective and practically sustainable.
 
### Context 📜
 
Depression is one of the most common conditions general practitioners see, and many patients are treated in primary care rather than by specialists. Collaborative care is a well-evidenced way of improving that care: the GP works together with a care manager and a mental health specialist, with structured follow-up of the patient's symptoms. Its effectiveness has been shown in many randomised controlled trials (RCTs).
 
Collaborative care is not a single intervention but a package of components, such as care management, symptom monitoring, specialist supervision, psychological support and medication management. Delivering the full package takes staff time and resources that many practices do not have.
 
### The Challenge 🧩
 
The existing evidence shows that collaborative care works **on average**, but it does not tell a GP which components drive the effect, or which combination is best for the patient in front of them. This project therefore asks which components, alone and in combination, lead to better depression outcomes, and how these effects differ between patients with different profiles, such as baseline severity, age, sex or medical history.
 
Answering these questions requires analysing participant-level data from many trials together. Each trial, however, recorded its data differently, with its own variable names, depression instruments, follow-up schedules and codings, so the data first has to be harmonised into one consistent, pooled dataset. On this basis, the project explores whether an individual patient's likely response to different combinations of components can be predicted, and how such predictions can be presented in a tool that GPs find intuitive and can use within their time and resource constraints.

### Project Goal and Contributions 🚀

The goal of this project is to support personalized collaborative care for depression in German general practice. We contribute in the following ways:

- **Harmonized pooled dataset:** a reproducible pipeline that exports, harmonizes, merges and enriches participant-level data from multiple collaborative care RCTs into one analysis-ready dataset.
- **Clinical prediction model:** a component network meta-analysis (CNMA) and risk-score modelling on the pooled data, to estimate how collaborative care components affect outcomes for different patients.
- **Web prototype:** a prototype tool showing how these insights could be brought into general practice.
- **Documentation:** technical documentation of the data pipeline, modelling approach and suggestions for future work.

## A Note on the Data 🔒

The trial data is confidential participant-level data. It is shared with the team separately and is never committed to this repository. Before working with it, please read [AGENTS.md](AGENTS.md): in short, look only at schemas and aggregates, never at individual records.

## How to Use the Code 🛠️

### Set up the environment

We use [uv](https://docs.astral.sh/uv/getting-started/installation/) to manage Python and dependencies. Once it is installed:

```bash
git clone https://github.com/DSSGxMunich/collaborative-care-analysis.git
cd collaborative-care-analysis
uv sync
```

### Add the data

Place the raw trial folders in `data/raw/Individual Datasets/` and extract the POOL2 export once:

```bash
unzip data/raw/260810_POOL2.zip -d data/raw/260810_POOL2
```

### Run the pipeline

One command takes every trial from its raw files to a single harmonized dataset:

```bash
uv run collaborative_care_analysis/dataset.py run
```

The result lands in `data/interim/enriched_dataset/`. You can also run a single study (`run 17`) or leave some out (`run -x 04`). The individual steps (`export`, `harmonize`, `merge`, `enrich`) are covered in the docs.

### Run the tests

```bash
uv run pytest
```

Most tests check the pipeline output, so run the pipeline first. Otherwise they are skipped.

### Run the notebooks

The notebooks in `notebooks/` cover the cohort filtering and the CNMA model. Open them in Jupyter (`uv run jupyter lab`) or in VS Code with the `.venv` kernel selected.

## Structure of the Repository 📁

```
collaborative-care-analysis/
├── collaborative_care_analysis/   # Source code: data loaders, harmonization, pipeline, analysis
├── data/                          # Raw and processed data (not tracked by git)
├── docs/                          # Technical documentation (MkDocs)
├── models/                        # Fitted models
├── notebooks/                     # Exploration and modelling notebooks
├── tests/                         # Checks on the pipeline output
├── AGENTS.md                      # Data privacy rules
├── HARMONIZATION_CONVENTIONS.md   # How harmonized variables are named and coded
└── pyproject.toml                 # Dependencies and tool configuration
```

## Technical Documentation 📚

The documentation goes into much more detail on the pipeline, the datasets, the models and how to add a new study. To browse it locally, run:

```bash
uv run mkdocs serve -f docs/mkdocs.yml
```

Then open http://127.0.0.1:8000. The pages live in `docs/docs/`. Any change you save shows up in the browser straight away.

## How to Contribute 🤝

1. Create a branch with a descriptive name.
2. Make your changes, following the [harmonization conventions](HARMONIZATION_CONVENTIONS.md).
3. Lint and test: `uv run ruff check . --fix && uv run ruff format && uv run pytest`
4. Open a pull request against `main`.

Optionally, `uvx pre-commit install` runs these checks for you on every commit, and `nbstripout --install` keeps notebook outputs out of git.

## Requesting Features or Reporting Bugs 🐞

Found a bug or have an idea? Please open an issue. Remember not to include any data values in it.
