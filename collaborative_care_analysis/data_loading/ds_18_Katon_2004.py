import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(file_path=RAW_DATASETS_DIR / "18_Katon_2004" / "katon2004.CLEANED.sav"):
    return pd.read_spss(file_path)
