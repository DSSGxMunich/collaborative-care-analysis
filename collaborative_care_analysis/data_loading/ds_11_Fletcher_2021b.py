import re

import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

TIMEPOINT_TO_MONTHS = {
    1: 0,
    2: 3,
    3: 12,
}

TIMEPOINT_PATTERN = re.compile(r"^(?P<stub>.+)_(?P<timepoint>[1-3])$")

TIME_INDEPENDENT_COLS = [
    "risk",
    "group",
    "DOB",
    "AGE",
    "AGE_int",
    "AGE_grp",
    "AGE_grp3",
]


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape numbered timepoint variables from wide to long format."""
    timepoint_cols = [col for col in df.columns if TIMEPOINT_PATTERN.match(col)]

    screening_cols = [col for col in df.columns if col.endswith("_0")]

    # "_t" columns are toolkit variables rather than numbered follow-up measures.
    # Keep them separate and attach them to the baseline row only.
    toolkit_cols = [col for col in df.columns if col.endswith("_t")]

    # Verify every raw column is accounted for.
    expected_cols = {
        "study_id",
        *TIME_INDEPENDENT_COLS,
        *timepoint_cols,
        *screening_cols,
        *toolkit_cols,
    }

    unaccounted = set(df.columns) - expected_cols
    if unaccounted:
        raise ValueError(f"Unaccounted columns: {sorted(unaccounted)}")

    # Determine all longitudinal variable names while preserving their
    # original column order.
    stubs = []
    for col in df.columns:
        match = TIMEPOINT_PATTERN.match(col)
        if match:
            stub = match.group("stub")
            if stub not in stubs:
                stubs.append(stub)

    reserved_cols = set(TIME_INDEPENDENT_COLS) | set(screening_cols) | set(toolkit_cols)

    collisions = set(stubs) & reserved_cols
    if collisions:
        raise ValueError(
            f"Time-varying variable names collide with retained columns: {sorted(collisions)}"
        )

    frames = []

    for timepoint, months in TIMEPOINT_TO_MONTHS.items():
        # Build the patient-level part.
        visit = df[["study_id"] + TIME_INDEPENDENT_COLS].copy()

        visit.rename(
            columns={"study_id": "patient_id"},
            inplace=True,
            errors="raise",
        )

        visit.insert(
            loc=1,
            column="follow_up_months",
            value=months,
        )

        # Build all time-varying columns at once to avoid DataFrame
        # fragmentation from repeated column insertion.
        time_varying = {}

        for stub in stubs:
            raw_col = f"{stub}_{timepoint}"

            if raw_col in df.columns:
                time_varying[stub] = df[raw_col].astype("object")
            else:
                time_varying[stub] = pd.Series(
                    pd.NA,
                    index=df.index,
                    dtype="object",
                )

        time_varying_df = pd.DataFrame(
            time_varying,
            index=df.index,
        )

        # TODO: Confirm whether toolkit variables should be assigned to baseline
        # or handled separately in downstream harmonization.

        # Screening ("_0") and toolkit ("_t") variables belong to the
        # pre-randomization/baseline data collection and are kept separate from
        # the numbered longitudinal assessments.
        baseline_cols = screening_cols + toolkit_cols

        if months == 0:
            baseline_df = df[baseline_cols].astype("object")
        else:
            baseline_df = pd.DataFrame(
                {
                    col: pd.Series(
                        pd.NA,
                        index=df.index,
                        dtype="object",
                    )
                    for col in baseline_cols
                }
            )

        visit = pd.concat(
            [
                visit.reset_index(drop=True),
                baseline_df.reset_index(drop=True),
                time_varying_df.reset_index(drop=True),
            ],
            axis=1,
        )

        frames.append(visit)

    long = (
        pd.concat(frames, ignore_index=True)
        .sort_values(
            ["patient_id", "follow_up_months"],
            kind="stable",
        )
        .reset_index(drop=True)
    )

    # Drop visit rows with no time-varying data recorded.
    long.dropna(
        subset=stubs + screening_cols + toolkit_cols,
        how="all",
        inplace=True,
    )

    long.reset_index(drop=True, inplace=True)

    if long.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    return long


def load(
    file_path=RAW_DATASETS_DIR / "11_Fletcher_2021b" / "TargetD_ForAnalysis.dta",
) -> pd.DataFrame:
    """Load Fletcher 2021b and return it in long format."""
    df = pd.read_stata(
        file_path,
        convert_categoricals=False,
    )

    # Treat blank or whitespace-only strings as missing values.
    df = df.replace(
        to_replace=r"^\s*$",
        value=pd.NA,
        regex=True,
    )

    df.dropna(how="all", axis="index", inplace=True)
    df.dropna(how="all", axis="columns", inplace=True)
    df.columns = df.columns.str.strip()

    assert df["study_id"].notna().all(), "Rows with missing study_id"

    if df["study_id"].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    df = to_long(df)

    # Convert columns to the best dtypes that support pd.NA.
    df = df.convert_dtypes()

    return df
