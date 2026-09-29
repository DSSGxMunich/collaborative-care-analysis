# Known issues

These inconsistencies were found while writing these docs (September 2026).
They are listed here so they do not surprise anyone; they have not been fixed.

## Analysis hand-offs do not line up

| Where                                          | Expects                                                                                   | Actually exists                                                        |
|------------------------------------------------|-------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| `risk_score_model.R` input                     | `data/interim/analysis_datasets/phq9_12mo_core/wide.csv` with `phq9_total_baseline` / `phq9_total_outcome` | `dataset_creation.create_wide()` writes `analysis_dataset_wide.csv` with `baseline_phq9` / `phq9_12mo` |
| `risk_score_model.R` error message             | `uv run collaborative_care_analysis/dataset.py analysis-data`                             | `dataset.py` has no `analysis-data` command                            |
| `02_CNMA_version1.ipynb`                       | imports a `risk_score_dataset` module                                                     | no such module in the repository                                       |
| `02_CNMA_version1.ipynb`                       | `data/processed/risk_scores.csv` with a `risk_score` column                               | nothing in the repository writes this file                            |

Until these are reconciled, running Step 1 → Step 2 end to end needs manual
steps or code that is not in `main`.

## Dependencies not declared

- The CNMA notebook imports **PyMC** and **ArviZ**. Neither is in
  `pyproject.toml`.
- The R script needs **R** with `data.table` and `ordinal`. These are not
  managed by uv.

## Pipeline coverage

- `29_Simon_2011` has a loader but no harmonizers, so it is not in the merged
  dataset.
- `16`, `18` and `28` have no `medical_history` cluster.
- The treatment cluster currently only produces `study_arm`, as noted in the
  harmonizers ("LIMITATION discussed on 02.09.2026"). Intervention content
  comes only from the enrichment sheet.
- `harmonization_column_clusters/` exists but contains no scripts.

## Documentation drift

- The README's project tree lists files that do not exist (see
  [Project layout](project-layout.md)).
- The README says generated codebooks have three sheets. `codebook.py`
  currently writes a single **Codebook** sheet.
- `HARMONIZATION_CONVENTIONS.md` and `docs/docs/harmonization-conventions.md`
  are two copies of the same file and must be updated together.
