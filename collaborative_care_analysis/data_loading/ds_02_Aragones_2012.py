import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Aragonès 2012 = the INDI project (cluster RCT, 20 primary-care centres,
# 338 patients with DSM-IV major depression, arms: multi-component depression
# management programme vs. usual care). Outcomes assessed by a blinded phone
# interviewer at 0, 3, 6 and 12 months; primary outcome PHQ-9.
#
# The study's raw folder is shared with Aragonès 2019 (ds_03). This loader uses
# ``indi_christos.csv`` -- the INDI/2012 patient-level export (338 rows, PHQ-9
# totals + item 9 at each of the four visits). ``DROP_Christos.csv`` in the same
# folder is the 2019 study and is loaded by ds_03. The ``*.sui.dta`` files in
# the folder are a reduced meta-analysis format that keeps only baseline and a
# single 6-month follow-up, so they are not used here.

TIME_INDEPENDENT_COLS = [
    "Cluster",
    "gr_est",
    "age",
    "sex",
    "HYPERT",
    "DIABETES",
    "RESPIRATORY",
    "CARDIOVASC",
    "CANCER",
    "CHRONICCON",
    "dtotal",
]

# raw wide column -> stub name shared across visits
TIMEPOINT_COLS = {
    0: {"phq90tp": "phq9_total", "phq909": "phq9_9"},
    3: {"phq93tp": "phq9_total", "phq939": "phq9_9"},
    6: {"phq96tp": "phq9_total", "phq969": "phq9_9"},
    12: {"phq912tp": "phq9_total", "phq9129": "phq9_9"},
}


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape the repeated PHQ-9 measurements from wide to long format."""
    frames = []

    for months, column_mapping in TIMEPOINT_COLS.items():
        visit = df[["ip1"] + TIME_INDEPENDENT_COLS + list(column_mapping)].copy()

        visit.rename(
            columns={"ip1": "patient_id", **column_mapping},
            inplace=True,
            errors="raise",
        )

        visit.insert(loc=1, column="follow_up_months", value=months)

        frames.append(visit)

    long = (
        pd.concat(frames, ignore_index=True)
        .sort_values(["patient_id", "follow_up_months"], kind="stable")
        .reset_index(drop=True)
    )

    if long.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    return long


def load(
    file_path=RAW_DATASETS_DIR / "02_03_Aragones_2012_2019" / "Aragones" / "indi_christos.csv",
) -> pd.DataFrame:
    """Load dataset Aragonès 2012 (INDI) and return it in long format."""
    df = pd.read_csv(file_path)
    df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)

    df.dropna(how="all", axis="index", inplace=True)
    df.dropna(how="all", axis="columns", inplace=True)
    df.columns = df.columns.str.strip()

    assert df["ip1"].notna().all(), "Rows with missing patient id"
    if df["ip1"].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    expected_cols = {
        "ip1",
        *TIME_INDEPENDENT_COLS,
        *(col for mapping in TIMEPOINT_COLS.values() for col in mapping),
    }

    unaccounted = set(df.columns) - expected_cols
    missing = expected_cols - set(df.columns)
    if unaccounted:
        raise ValueError(f"Unaccounted columns: {sorted(unaccounted)}")
    if missing:
        raise ValueError(f"Expected columns missing from dataset: {sorted(missing)}")

    # Every column in this export is numeric, but the blanks make ``read_csv``
    # parse some of them as ``object`` holding digit strings. Left alone, the
    # baseline PHQ-9 columns (no blanks -> int64) and the follow-up ones (blanks
    # -> object) stack into a single column mixing Python ``int`` and ``str``,
    # which raises on any comparison. Coerce up front so ``load()`` is usable
    # without every consumer re-coercing.
    df = df.apply(pd.to_numeric, errors="raise")

    df = to_long(df)

    return df.convert_dtypes()
