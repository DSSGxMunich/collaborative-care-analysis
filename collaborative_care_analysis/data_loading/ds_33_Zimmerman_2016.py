from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

# Files in this study's raw folder:
#   IPD-SMADS-NCT01726387-325pat-phq9 (1).dta -> other individual-patient file,
#                                                  not used by this loader
#   Zimmermann_2016.sui.dta                    -> source file used by this loader
#   Zimmermann 2016.pdf                        -> published trial paper
#
# ``Group`` is INVERTED in this export and is corrected on load (see
# GROUP_RELABEL). The file labels 191 patients "Intervention" and 134
# "Control"; the paper says the opposite -- "325 participants (IG N = 134, CG
# N = 191)" and "patients were enrolled in the intervention group (IG), 191 in
# the control group (CG)". Its completion percentages only work that way round
# (61/134 = 45.5%, 107/191 = 56.0%, 94/134 = 70.1%), and this file's 12-month
# completers are 107 for the group it calls "Intervention", which is the
# paper's CG figure exactly. Left uncorrected, this study's treatment effect
# enters the meta-analysis with its arms reversed.


# These are the only visit timings that are confirmed for this file.
# ``_0`` denotes baseline and ``_f3`` denotes 12-month follow-up.
TIMEPOINT_COLS = {
    0: {
        "Depres_0": "Depression_severity",
        "ZDepres_0": "ZDepression_severity",
        "Suic_0": "Suicidality",
        "ZSuic_0": "ZSuicidality",
        "Medadh_0": "medication_adherence",
    },
    12: {
        "Depres_f3": "Depression_severity",
        "ZDepres_f3": "ZDepression_severity",
        "Suic_f3": "Suicidality",
        "ZSuic_f3": "ZSuicidality",
    },
}


# The export's arm labels are the wrong way round (see the note above), so they
# are swapped back to the paper's assignment on load.
GROUP_RELABEL = {"Intervention": "Control", "Control": "Intervention"}


# TODO: Add this to TIMEPOINT_COLS once its follow-up month is confirmed.
UNRESOLVED_TIME_COLS = ["Medadh_f"]


# These source columns contain no observed values in this dataset. Listing
# them explicitly to document why they do not appear in the harmonized output.
KNOWN_EMPTY_COLS = [
    "LTC_Mes",
    "LTC_inclType",
    "LTC_emp",
    "Medadh_Mes",
    "LTC_0",
    "LTCn_0",
    "LTCsev_0",
    "Diabetes",
    "Hypertension",
    "Cardiac",
    "Respiratory",
    "Cancer",
]


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

    ``Medadh_0`` supplies medication adherence at baseline. The timing
    represented by ``Medadh_f`` is not known, so that source column is omitted
    until its follow-up month can be confirmed.
    """
    id_col = "Origpat_id"
    time_varying_cols = {
        source_col for column_mapping in TIMEPOINT_COLS.values() for source_col in column_mapping
    }
    static_cols = [
        col
        for col in df.columns
        if col != id_col and col not in time_varying_cols and col not in UNRESOLVED_TIME_COLS
    ]

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
        "medication_adherence",
        "TriaI_id",
        "DepresSev_Mes",
        "LTC_incl",
        "Group",
        "Cluster",
        "Sex",
        "Age",
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

    missing_id = df["Origpat_id"].isna()
    if missing_id.any():
        logger.warning(f"Dropped {int(missing_id.sum())} rows with missing Origpat_id.")
        df = df.loc[~missing_id]

    duplicated_id = df["Origpat_id"].duplicated(keep=False)
    if duplicated_id.any():
        logger.warning(f"Dropped {int(duplicated_id.sum())} rows with duplicated Origpat_id.")
        df = df.loc[~duplicated_id]

    df["Group"] = map_with_check(df["Group"], GROUP_RELABEL)

    unexpectedly_nonempty = [col for col in KNOWN_EMPTY_COLS if df[col].notna().any()]
    if unexpectedly_nonempty:
        raise ValueError(
            "Columns expected to be empty now contain observations: "
            f"{sorted(unexpectedly_nonempty)}"
        )

    # ``Time`` is deliberately excluded: its meaning conflicts with the
    # confirmed _0/baseline and _f3/12-month suffixes. The known-empty columns
    # are removed only after verifying that they contain no observations.
    df.drop(columns=["Time", *KNOWN_EMPTY_COLS], inplace=True, errors="raise")

    return to_long(df).convert_dtypes()
