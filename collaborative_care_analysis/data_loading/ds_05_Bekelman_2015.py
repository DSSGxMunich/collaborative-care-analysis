import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    long_file_path=RAW_DATASETS_DIR / "05_Bekelman_2015" / "Schillok_PCDM_condensed_long.csv",
    wide_file_path=RAW_DATASETS_DIR / "05_Bekelman_2015" / "Schillok_PCDM_condensed_wide.csv",
):
    # Load long dataset containing questionnaire responses
    df_long = pd.read_csv(long_file_path)

    # Load wide dataset containing demographic and patient-level data
    df_wide = pd.read_csv(wide_file_path)

    # Merge both datasets using patient ID
    df = df_long.merge(
        df_wide,
        on="pt_id",
        how="left",
        validate="many_to_one",
    )

    return df
