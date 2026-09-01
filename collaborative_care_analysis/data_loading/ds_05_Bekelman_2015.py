import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check


def load(
    long_file_path=RAW_DATASETS_DIR / "05_Bekelman_2015" / "Schillok_PCDM_condensed_long.csv",
    wide_file_path=RAW_DATASETS_DIR / "05_Bekelman_2015" / "Schillok_PCDM_condensed_wide.csv",
):
    # Load long dataset containing questionnaire responses
    df_long = pd.read_csv(long_file_path)

    # Load wide dataset containing demographic and patient-level data
    df_wide = pd.read_csv(wide_file_path)

    # Drop empty and redundant columns.
    df_long.drop(labels="Unnamed: 0", axis=1, errors="raise", inplace=True)
    df_wide.drop(labels="Unnamed: 0", axis=1, errors="raise", inplace=True)

    # Merge both datasets using patient ID
    if df_long.duplicated(["pt_id", "surv_version"]).any():
        raise ValueError("Duplicate patient/time-point combinations")
    df = df_long.merge(
        df_wide,
        on="pt_id",
        how="inner",
        validate="many_to_one",
    )

    # Merge tables on the unique patient ids.
    df.dropna(how="all", axis=0, inplace=True)
    df.dropna(how="all", axis=1, inplace=True)
    df.columns = df.columns.str.strip()

    assert df["pt_id"].notna().all(), "Rows with missing pt_id"
    assert df["surv_version"].notna().all(), "Rows with missing surv_version"

    # Safely rename pt_id and surv_version columns.
    df.rename(columns={"pt_id": "patient_id"}, inplace=True, errors="raise")
    df.insert(
        loc=1,
        column="follow_up_months",
        value=map_with_check(
            series=df["surv_version"],
            mapping={"baseline": 0, "3month": 3, "6month": 6, "final": 12},
        ),
    )
    df.drop(labels="surv_version", axis=1, errors="raise", inplace=True)

    # Convert columns to the best dtypes that support pd.NA
    df = df.convert_dtypes()

    return df
