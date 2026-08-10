# Collaborative Care Analysis

Depression Treatment Navigator for Primary Care

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
