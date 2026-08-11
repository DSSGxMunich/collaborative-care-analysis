import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(file_path=RAW_DATASETS_DIR / "27_Simon_2000" / "simon2000.CLEANED.sav"):
    return pd.read_spss(file_path)
