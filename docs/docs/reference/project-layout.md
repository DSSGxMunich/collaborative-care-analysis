# Project layout

```text
collaborative-care-analysis/
├── AGENTS.md                         data privacy rules (humans and AI agents)
├── HARMONIZATION_CONVENTIONS.md      naming and coding rules for harmonized data
├── README.md
├── pyproject.toml / uv.lock          dependencies and tool configuration
├── .pre-commit-config.yaml           ruff, full pipeline run, uv-lock
├── .github/workflows/lint.yml        CI: ruff check + format check
│
├── collaborative_care_analysis/      the Python package
│   ├── config.py                     paths and constants
│   ├── dataset.py                    pipeline CLI: export / harmonize / merge / enrich / run
│   ├── utils.py                      map_with_check, ensure_unzipped, labeled_variables
│   ├── pool2.py                      POOL2 side loader and age/sex backfill
│   ├── enrichment.py                 study-arm-level treatment characteristics
│   ├── codebook.py                   Excel codebooks from SPSS/Stata metadata
│   ├── agent/
│   │   └── inspect_metadata.py       terminal schema / aggregate inspection
│   ├── data_loading/                 one loader per trial: ds_<NN>_<Author>_<Year>.py
│   ├── harmonization_baseline/       ┐
│   ├── harmonization_medical_history/│ one harmonizer per trial and cluster
│   ├── harmonization_outcomes/       │
│   ├── harmonization_treatment/      ┘
│   └── data_analysis/
│       ├── dataset_creation.py       baseline + 12-month analysis cohort
│       └── risk_score_model.R        Step 1 proportional-odds mixed model
│
├── notebooks/
│   ├── 01_filter_datasets.ipynb      cohort attrition audit
│   └── 02_CNMA_version1.ipynb        Step 2 Bayesian component network model
│
├── tests/                            pytest suite on pipeline outputs
├── docs/                             this MkDocs site
│
├── data/                             git-ignored except the annotation CSVs
│   ├── raw/                          immutable source data
│   ├── interim/                      pipeline outputs
│   ├── processed/                    final data for modeling (for example risk_scores.csv)
│   └── external/                     third-party data
├── models/                           fitted models (for example risk_score_model.rds)
├── references/                       manuals, data dictionaries
└── reports/figures/                  generated figures
```

!!! note
    The README's "Project Organization" section comes from the Cookiecutter
    Data Science template. It still lists `features.py`, `plots.py`,
    `modeling/`, `setup.cfg` and `LICENSE`, which do not exist in the
    repository. The tree above shows the actual layout.
