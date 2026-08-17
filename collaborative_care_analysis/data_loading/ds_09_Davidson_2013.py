import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


#I chose this dataset instead of the other since they are similar in both shape and content (I checked)
def load(file_path=RAW_DATASETS_DIR / "09_Davidson_2013" / "Davidson 2013 CLEANED.sav"):
    return pd.read_spss(file_path)