import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(file_path=RAW_DATASETS_DIR / "11_Fletcher_2021b" / "TargetD_ForAnalysis.dta"):
    return pd.read_stata(file_path)
