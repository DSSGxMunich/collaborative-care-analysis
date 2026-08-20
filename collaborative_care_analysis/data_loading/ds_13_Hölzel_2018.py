import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

TIMEPOINT_MAP = {
    "B1": 0,
    "B2": 6,
    "B3": 12,
}


def load(
    file_path=RAW_DATASETS_DIR
    / "13_Hölzel_2018"
    / "Daten"
    / "20231120_German_IMPACT_f__r_IPD_MA.sav",
) -> pd.DataFrame:
    """
    Load the German IMPACT dataset and reshape it to longitudinal format.

    The SPSS and Stata files contain the same information. The SPSS file is
    used because its column names and variable coding are clearer.
    """

    df = pd.read_spss(
        path=file_path,
        convert_categoricals=True,
    )

    # Remove rows and columns containing only missing values.
    df.dropna(how="all", axis="index", inplace=True)
    df.dropna(how="all", axis="columns", inplace=True)

    # Remove leading and trailing whitespace from column names.
    df.columns = df.columns.str.strip()

    # Rename identifiers used across the harmonization pipeline.
    df.rename(
        columns={
            "ID": "patient_id",
            "RG": "study_arm",
        },
        inplace=True,
    )

    # Store patient identifiers as strings.
    df["patient_id"] = df["patient_id"].astype("string").str.replace(r"\.0$", "", regex=True)

    # Translate the treatment-group values.
    df["study_arm"] = (
        df["study_arm"]
        .astype("string")
        .replace(
            {
                "IG": "intervention",
                "KG": "control",
            }
        )
    )

    # Identify columns that are not specific to B1, B2, or B3.
    timepoint_prefixes = tuple(f"GI_{timepoint}_" for timepoint in TIMEPOINT_MAP)

    # These PHQ columns encode the month directly in the column name.
    phq_month_cols = {
        f"PHQ_{follow_up_months}_Monate"
        for follow_up_months in TIMEPOINT_MAP.values()
        if f"PHQ_{follow_up_months}_Monate" in df.columns
    }

    # Static columns do not encode an assessment time.
    static_cols = [
        col
        for col in df.columns
        if (not col.startswith(timepoint_prefixes) and col not in phq_month_cols)
    ]

    longitudinal_dfs = []

    for timepoint, follow_up_months in TIMEPOINT_MAP.items():
        prefix = f"GI_{timepoint}_"

        timepoint_cols = [col for col in df.columns if col.startswith(prefix)]

        # Define the mapping before using it.
        timepoint_rename_map = {col: col.replace(prefix, "GI_", 1) for col in timepoint_cols}

        # Add PHQ_X_Monate to the corresponding assessment.
        phq_month_col = f"PHQ_{follow_up_months}_Monate"

        if phq_month_col in df.columns:
            timepoint_cols.append(phq_month_col)
            timepoint_rename_map[phq_month_col] = "PHQ_Monate"

        # Check whether each patient has any data at this time point.
        has_timepoint_data = df[timepoint_cols].notna().any(axis=1)

        timepoint_df = (
            df.loc[
                has_timepoint_data,
                static_cols + timepoint_cols,
            ]
            .rename(columns=timepoint_rename_map)
            .copy()
        )

        timepoint_df["follow_up_months"] = follow_up_months

        longitudinal_dfs.append(timepoint_df)

    df = pd.concat(
        longitudinal_dfs,
        ignore_index=True,
    )

    # Put the main identifiers first.
    front_cols = [
        "patient_id",
        "study_arm",
        "follow_up_months",
    ]

    df = df[front_cols + [col for col in df.columns if col not in front_cols]]

    return df
