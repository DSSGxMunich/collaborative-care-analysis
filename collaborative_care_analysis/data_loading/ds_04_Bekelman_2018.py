import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(file_path=RAW_DATASETS_DIR / "04_Bekelman_2018" / "CASAforIPD-MA (1).csv"):
    return pd.read_csv(file_path)
