# Harmonization

Harmonization maps each trial's variables onto a shared set of names and
codings. The work is split into **clusters**, which are thematic groups of
variables. Each cluster is a folder in the package:

| Folder                             | Cluster name       | Contents                                                                     |
|------------------------------------|--------------------|------------------------------------------------------------------------------|
| `harmonization_baseline/`          | `baseline`         | Demographics: `age`, `sex`, and other baseline characteristics               |
| `harmonization_medical_history/`   | `medical_history`  | Comorbidities and history (for example `chronic_disease_score`)              |
| `harmonization_outcomes/`          | `outcomes`         | Symptom scales: PHQ-9, GAD-7, SCL-20, HSCL, BDI, CES-D, K10, HRSD-17, CIS-R, PROMIS, EQ-5D, SF-12/36, … |
| `harmonization_treatment/`         | `treatment`        | `study_arm` (`"control"` / `"intervention"`)                                 |

Inside each folder there is one script per study, named exactly like its loader
(`ds_17_Katon_2001.py`).

## How discovery works

`dataset.py harmonize` does the following for each selected study:

1. Calls the loader's `load()` and inserts `STUDY_ID` as the first column.
2. Finds every `harmonization_*` folder in the package. The folder name must
   be a valid Python identifier.
3. In each folder, finds the scripts whose name matches the study, by full
   stem, number or name.
4. Imports each script and collects its **harmonization functions**:
    - all public functions whose name starts with `harmoniz` (`harmonize`,
      `harmonize_baseline`, `harmonize_outcomes`, …), or,
    - if there are none, every public function defined in the module.
5. Calls each function on a **copy** of the loaded frame and writes the result
   to `harmonized_datasets/ds_<NN>_<Name>_<cluster>.csv`.

If one script defines several harmonization functions, each gets its own file
with the suffix `<cluster>-<function-suffix>`. For example,
`harmonize_scores` in `harmonization_outcomes` produces `…_outcomes-scores.csv`.

### Checks applied to each function's output

| Condition                              | Result                  |
|----------------------------------------|-------------------------|
| Function returned `None`               | `ValueError`            |
| `STUDY_ID` column was removed          | `ValueError`            |
| Row count differs from the input       | Warning (rows dropped)  |

## The harmonizer contract

A harmonization function:

- takes the loaded frame (with `STUDY_ID`) and returns a new frame,
- **must return the join keys** `STUDY_ID`, `patient_id`, `follow_up_months`,
- returns **only** that cluster's harmonized columns. Every non-key column name
  must be unique across the study's clusters, or the merge fails,
- recodes categories to descriptive labels with `map_with_check`,
- keeps missing values missing. It never fills them with `"no"` or `0`.

Example from `harmonization_baseline/ds_17_Katon_2001.py`:

```python
ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]
SEX_MAPPING = {0: "Male", 1: "Female"}


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize baseline variables for Katon 2001."""
    out = df[ID_COLS + ["age", "gender"]].copy()
    out["sex"] = map_with_check(out["gender"], SEX_MAPPING).astype("category")
    out = out.drop(columns=["gender"])
    out["age"] = pd.to_numeric(out["age"], errors="raise")
    return out
```

And from `harmonization_treatment/ds_17_Katon_2001.py`:

```python
def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["study_arm"] = map_with_check(df["grp"], {1.0: "control", 2.0: "intervention"})
    return df[["STUDY_ID", "patient_id", "study_arm", "follow_up_months"]]
```

## Naming and coding rules

All harmonized columns follow the
[Harmonization conventions](../harmonization-conventions.md). In short:

- lowercase `snake_case`, and descriptive rather than short,
- timing goes in `follow_up_months`, never in a column name,
- scales use `<instrument>_<item>` and `<instrument>_total` (`phq9_1` … `phq9_9`,
  `phq9_total`). Different instruments keep different prefixes (`bdi1_*` and
  `bdi2_*`, for example),
- categories are stored as labels (`"yes"`/`"no"`, `"control"`/`"intervention"`,
  `"Male"`/`"Female"`), not numeric codes.

## Adding a cluster

To add a new cluster, create a folder `harmonization_<name>/` in the package
and add per-study scripts. It is discovered automatically. Its outputs are
joined in at merge time, and its columns are listed under `<name>` in the
merge's cluster-to-columns mapping.

!!! note
    Cluster names are matched longest-first when the merge splits file names
    back into (study, cluster). This means a cluster whose name contains
    another one (for example `outcomes_secondary` and `outcomes`) still
    resolves correctly.
