import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Files in this study's raw folder:
#   IPD-SMADS-NCT01726387-325pat-phq9 (1).dta -> other individual-patient file,
#                                                  not used by this loader
#   Zimmermann_2016.sui.dta                    -> source file used by this loader
#   Zimmermann 2016.pdf                        -> published trial paper


# These are the only visit timings that are confirmed for this file.
# ``_0`` denotes baseline and ``_f3`` denotes 12-month follow-up.
TIMEPOINT_COLS = {
    0: {
        "Depres_0": "Depression_severity",
        "ZDepres_0": "ZDepression_severity",
        "Suic_0": "Suicidality",
        "ZSuic_0": "ZSuicidality",
    },
    12: {
        "Depres_f3": "Depression_severity",
        "ZDepres_f3": "ZDepression_severity",
        "Suic_f3": "Suicidality",
        "ZSuic_f3": "ZSuicidality",
    },
}


# Listing the source columns explicitly makes the loader fail if a future file
# has an unexpected schema instead of silently discarding new information.
EXPECTED_SOURCE_COLS = {
    "TriaI_id",
    "Time",
    "DepresSev_Mes",
    "LTC_Mes",
    "LTC_incl",
    "LTC_inclType",
    "LTC_emp",
    "Medadh_Mes",
    "Origpat_id",
    "Group",
    "Cluster",
    "Sex",
    "Age",
    "Depres_0",
    "Depres_f3",
    "Medadh_0",
    "Medadh_f",
    "LTC_0",
    "LTCn_0",
    "LTCsev_0",
    "Diabetes",
    "Hypertension",
    "Cardiac",
    "Respiratory",
    "Cancer",
    "ZDepres_0",
    "ZDepres_f3",
    "Suic_0",
    "Suic_f3",
    "ZSuic_0",
    "ZSuic_f3",
    "year",
    "country",
    "recruitmentmethod",
    "patientsample",
    "euc",
    "euccontinuous",
    "casemanagementbackground",
    "interventioncontent",
    "numberofsessions",
    "supervisionfrequency",
    "allocationconcealment",
    "ltc_meas",
    "author",
}


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape confirmed baseline and 12-month measures to long format.

    ``Medadh_0`` and ``Medadh_f`` remain separate columns and are repeated on
    both visit rows. The timing represented by ``Medadh_f`` is not known, so
    it must not be assigned to the 12-month visit.
    """
    id_col = "Origpat_id"
    time_varying_cols = {
        source_col for column_mapping in TIMEPOINT_COLS.values() for source_col in column_mapping
    }
    static_cols = [col for col in df.columns if col != id_col and col not in time_varying_cols]

    frames = []
    for months, column_mapping in TIMEPOINT_COLS.items():
        visit = df[[id_col, *static_cols, *column_mapping]].copy()
        visit.rename(
            columns={id_col: "patient_id", **column_mapping},
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

    # This is the complete harmonized output schema and column order.
    output_cols = [
        "patient_id",
        "follow_up_months",
        "Depression_severity",
        "ZDepression_severity",
        "Suicidality",
        "ZSuicidality",
        "TriaI_id",
        "DepresSev_Mes",
        "LTC_incl",
        "Group",
        "Cluster",
        "Sex",
        "Age",
        "Medadh_0",
        "Medadh_f",
        "year",
        "country",
        "recruitmentmethod",
        "patientsample",
        "euc",
        "euccontinuous",
        "casemanagementbackground",
        "interventioncontent",
        "numberofsessions",
        "supervisionfrequency",
        "allocationconcealment",
        "ltc_meas",
        "author",
    ]

    missing = set(output_cols) - set(long.columns)
    unexpected = set(long.columns) - set(output_cols)
    if missing or unexpected:
        raise ValueError(
            "Harmonized columns do not match the expected output schema. "
            f"Missing: {sorted(missing)}; unexpected: {sorted(unexpected)}"
        )

    return long[output_cols]


def load(
    file_path=RAW_DATASETS_DIR / "33_Zimmerman_2016" / "Zimmermann_2016.sui.dta",
) -> pd.DataFrame:
    """Load Zimmermann 2016 and return one row per patient and visit."""
    # Keep Stata's descriptive value labels. Convert categorical columns to
    # nullable strings so labelled "n/a" values can safely become missing.
    df = pd.read_stata(file_path)
    categorical_cols = df.select_dtypes(include="category").columns
    df[categorical_cols] = df[categorical_cols].astype("string")

    # Normalize blank strings and Stata's labelled "n/a" values before
    # removing empty rows and columns.
    df = df.replace(
        to_replace=[r"^\s*$", r"^n/a$"],
        value=pd.NA,
        regex=True,
    )
    df.dropna(how="all", axis="index", inplace=True)
    df.columns = df.columns.str.strip()

    missing = EXPECTED_SOURCE_COLS - set(df.columns)
    unaccounted = set(df.columns) - EXPECTED_SOURCE_COLS
    if missing:
        raise ValueError(f"Expected columns missing from dataset: {sorted(missing)}")
    if unaccounted:
        raise ValueError(f"Unaccounted columns: {sorted(unaccounted)}")

    if df["Origpat_id"].isna().any():
        raise ValueError("Rows with missing Origpat_id")
    if df["Origpat_id"].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    # ``Time`` is deliberately excluded: its meaning conflicts with the
    # confirmed _0/baseline and _f3/12-month suffixes.
    df.drop(columns="Time", inplace=True, errors="raise")

    # Columns containing no observations provide no patient information.
    df.dropna(how="all", axis="columns", inplace=True)

    return to_long(df).convert_dtypes()
