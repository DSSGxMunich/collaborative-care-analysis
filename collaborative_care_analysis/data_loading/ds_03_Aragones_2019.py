import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

TIME_INDEPENDENT_COLS = [
    "CLUSTER",
    "GROUP",
    "AGE",
    "SEX",
    "HYPERT",
    "DIABETES",
    "RESPIRATORY",
    "CARDIOVASCULAR",
    "CANCER",
    "CHR_CONDITIONS",
]

TIMEPOINT_COLS = {
    0: {
        "HSCLTOTb": "HSCLTOT",
        "HSCL_0_2": "HSCL_2",
    },
    3: {
        "HSCL_3_TOT": "HSCLTOT",
        "HSCL_3_2": "HSCL_2",
    },
    6: {
        "HSCL_6_TOT": "HSCLTOT",
        "HSCL_6_2": "HSCL_2",
    },
    12: {
        "HSCL_12_TOT": "HSCLTOT",
        "HSCL_12_2": "HSCL_2",
    },
}

def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape repeated HSCL measurements from wide to long format."""
    frames = []

    for months, column_mapping in TIMEPOINT_COLS.items():
        visit = df[["Id"] + TIME_INDEPENDENT_COLS + list(column_mapping)].copy()

        visit.rename(
            columns={
                "Id": "patient_id",
                **column_mapping,
            },
            inplace=True,
            errors="raise",
        )

        visit.insert(
            loc=1,
            column="follow_up_months",
            value=months,
        )

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
    file_path=RAW_DATASETS_DIR 
    / "02_03_Aragones_2012_2019" 
    / "Aragones" 
    / "DROP_Christos.csv",
) -> pd.DataFrame:
    """Load dataset Aragones 2019 and return it in long format."""
    df = pd.read_csv(file_path)
    df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)

    df.dropna(how="all", axis="index", inplace=True)
    df.dropna(how="all", axis="columns", inplace=True)
    df.columns = df.columns.str.strip()

    assert df["Id"].notna().all(), "Rows with missing Id"

    if df["Id"].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    expected_cols = {
        "Id",
        *TIME_INDEPENDENT_COLS,
        *(col for mapping in TIMEPOINT_COLS.values() for col in mapping),
    }

    unaccounted = set(df.columns) - expected_cols
    missing = expected_cols - set(df.columns)

    if unaccounted:
        raise ValueError(f"Unaccounted columns: {sorted(unaccounted)}")

    if missing:
        raise ValueError(f"Expected columns missing from dataset: {sorted(missing)}")

    df = to_long(df)

    df = df.convert_dtypes()

    return df
