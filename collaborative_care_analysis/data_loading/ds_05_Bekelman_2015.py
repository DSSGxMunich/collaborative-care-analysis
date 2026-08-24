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

    # Drop empty and redundant columns.
    df_long.drop(labels="Unnamed: 0", axis=1, errors="raise", inplace=True)
    df_wide.drop(labels="Unnamed: 0", axis=1, errors="raise", inplace=True)

    # Merge both datasets using patient ID
    df = df_long.merge(
        df_wide,
        on="pt_id",
        how="inner",
        validate="one_to_one",
    )

    # Merge tables on the unique patient ids.
    df.dropna(how="all", axis=0, inplace=True)
    df.dropna(how="all", axis=1, inplace=True)
    df.columns = df.columns.str.strip()

    return df
