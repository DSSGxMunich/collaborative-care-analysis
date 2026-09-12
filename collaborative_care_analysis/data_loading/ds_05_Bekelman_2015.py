from loguru import logger
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

    # A missing key would silently vanish in the inner join below (NaN never
    # matches), so check before merging, not after.
    missing_long = df_long["pt_id"].isna() | df_long["surv_version"].isna()
    if missing_long.any():
        logger.warning(f"Dropping {missing_long.sum()} row(s) with missing pt_id or surv_version.")
        df_long = df_long[~missing_long]

    missing_wide = df_wide["pt_id"].isna()
    if missing_wide.any():
        logger.warning(f"Dropping {missing_wide.sum()} row(s) with missing pt_id.")
        df_wide = df_wide[~missing_wide]

    dupes = df_long.duplicated(["pt_id", "surv_version"], keep=False)
    if dupes.any():
        n_patients = df_long.loc[dupes, "pt_id"].nunique()
        logger.warning(
            f"Dropping {dupes.sum()} row(s) sharing a duplicated (pt_id, surv_version) "
            f"({n_patients} patient(s) affected)."
        )
        df_long = df_long[~dupes]

    unmatched_long = ~df_long["pt_id"].isin(df_wide["pt_id"])
    if unmatched_long.any():
        logger.warning(f"{unmatched_long.sum()} row(s) have a pt_id absent from the wide file.")

    unmatched_wide = ~df_wide["pt_id"].isin(df_long["pt_id"])
    if unmatched_wide.any():
        logger.warning(
            f"{unmatched_wide.sum()} wide-file patient(s) have no rows in the long file."
        )

    df = df_long.merge(df_wide, on="pt_id", how="inner", validate="many_to_one")

    df.dropna(how="all", axis=0, inplace=True)
    df.dropna(how="all", axis=1, inplace=True)
    df.columns = df.columns.str.strip()

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
