import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(file_path=RAW_DATASETS_DIR / "21_Richards_2008" / "Richards 2008 CLEANED.sav"):
    return pd.read_spss(file_path)
