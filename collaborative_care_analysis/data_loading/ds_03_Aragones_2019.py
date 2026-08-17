import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(file_path=RAW_DATASETS_DIR / "02_03_Aragones_2012_2019" / "DROP_Christos.csv"):
    return pd.read_csv(file_path)