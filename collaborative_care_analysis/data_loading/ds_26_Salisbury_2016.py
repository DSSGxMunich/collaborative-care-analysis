import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR / "26_Salisbury_2016" / "Healthlines_Depression_trial_data.csv",
):
    return pd.read_csv(file_path)
