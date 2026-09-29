# Data loading

Every trial has one **loader** module in `collaborative_care_analysis/data_loading/`:

```text
data_loading/ds_<NN>_<FirstAuthor>_<Year>.py
```

The file name is significant. `NN` is the project's dataset number and the rest
is a descriptive name. Together they form the `STUDY_ID` (`17_Katon_2001`).

## The loader contract

A loader exposes one function, `load()`, which returns a `pandas.DataFrame`:

```python
def load(file_path=RAW_DATASETS_DIR / "17_Katon_2001" / "katon2001.sav") -> pd.DataFrame:
    ...
```

The returned frame must:

1. **Have a `patient_id` column**, renamed from the trial's own ID variable
   (`rename(..., errors="raise")`, so a typo fails immediately).
2. **Have a `follow_up_months` column** in months since baseline (baseline = `0`).
3. **Be in long format**: one row per patient per time point. Loaders for trials
   stored wide (`phq9_0`, `phq9_3`, …) must `melt` them.
4. **Be unique on `(patient_id, follow_up_months)`.** Most loaders check this
   and raise on duplicates.
5. **Use pandas nullable dtypes** (`Int64`, `Float64`, `string`, `boolean`),
   normally via `.convert_dtypes()`. `tests/test_loader_dtypes.py` enforces this.
6. **Not mix value types within a column** (for example ints and strings).

Loaders should *not* rename clinical variables to harmonized names. That is
the harmonizers' job. Loaders only fix structure.

## A typical loader

This is `ds_17_Katon_2001.py`, simplified:

```python
def load(file_path=RAW_DATASETS_DIR / "17_Katon_2001" / "katon2001.sav"):
    df = pd.read_spss(file_path).convert_dtypes()

    # blank strings -> missing
    df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)
    df = df.rename(columns={"id": "patient_id"}, errors="raise")

    # drop rows without an ID or a group
    df = df[df["patient_id"].notna() & df["grp"].notna()]

    # wide -> long: one SCL-20 column per visit
    SCL_FOLLOW_UP_MAP = {"bscl20": 0, "dscl20": 3, "escl20": 6, "fscl20": 9, "gscl20": 12}
    long_df = df.melt(
        id_vars=[c for c in df.columns if c not in SCL_FOLLOW_UP_MAP],
        value_vars=list(SCL_FOLLOW_UP_MAP),
        var_name="_follow_up_months",
        value_name="scl20_mean",
    )
    long_df["follow_up_months"] = map_with_check(long_df["_follow_up_months"], SCL_FOLLOW_UP_MAP)
    long_df = long_df.drop(columns=["_follow_up_months"])

    if long_df.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    return long_df.sort_values(["patient_id", "follow_up_months"]).convert_dtypes()
```

## Helpers in `utils.py`

| Function                                         | Use it to…                                                                 |
|--------------------------------------------------|---------------------------------------------------------------------------|
| `map_with_check(series, mapping)`                | Recode values with a dict and **fail if any non-null value is unmapped**. Plain `.map()` silently turns unknown codes into NaN, so use this instead. |
| `ensure_unzipped(zip_path, extract_dir, marker)` | Extract a zipped raw file on first use and skip extraction afterwards.     |
| `labeled_variables(dta_path)`                    | Return the set of variables with a non-empty label in a Stata file's metadata. |

## Reading raw formats

| Format     | Typical reader                                        |
|------------|-------------------------------------------------------|
| SPSS `.sav` | `pd.read_spss` or `pyreadstat.read_sav`              |
| Stata `.dta`| `pd.read_stata` or `pyreadstat.read_dta`             |
| CSV         | `pd.read_csv`                                        |
| Excel       | `pd.read_excel` (openpyxl)                           |

Before you write a loader, check the file's variables and value labels with
[`inspect_metadata`](../tools.md). You can do this without reading any
participant rows.
