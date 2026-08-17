import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# In this folder there is another datset (Schillok_PCDM_condensed_wide.csv) that has key demographic data (age, gender), that I didnt load yet but should do when we settle on the harmonization
# I chose this dataset because it has all of the questionaire responses and the other one doesn´t


def load(file_path=RAW_DATASETS_DIR / "05_Bekelman_2015" / "Schillok_PCDM_condensed_long.csv"):
    return pd.read_csv(file_path)
