import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Files in this study's raw folder:
#   IPD-SMADS-NCT01726387-325pat-phq9 (1).dta -> main individual patient dataset (325 patients,
#                                                 matches the trial's reported sample size), used below
#   Zimmermann_2016.sui.dta                    -> supplementary suicidality-focused dataset, may be used for later not now
#   Zimmermann 2016.pdf                        -> the published trial paper


def load(
    file_path=RAW_DATASETS_DIR / "33_Zimmerman_2016" / "IPD-SMADS-NCT01726387-325pat-phq9 (1).dta",
):
    return pd.read_stata(file_path)
