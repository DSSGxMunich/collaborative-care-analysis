import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


# I chose this dataset because it has all the information in the other dataset and more columns
def load(file_path=RAW_DATASETS_DIR / "08_Coventry_2015" / "coincidebasicn.sav"):
    return pd.read_spss(file_path)
