import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Files in this study's raw folder:
#   Codebook_Unützer et al. (2002).docx        -> variable/column definitions (reference only)
#   IMPACT_List of variables for the IPD analyses -> documents the exact variable set needed;
#                                                    matches the columns in Unutzer_2002.csv below (I checked it)
#   Impact depression severity study 2.sav/.csv -> broader raw trial data, not used here
#                                                   (missing several variables the IPD analysis needs)
#   unuex.dta / unutzer_2002.clean.do           -> Stata data/cleaning script, not used here
#   Unutzer 2002.pdf / Unützer 2002.pdf         -> the published trial paper
#   Unutzer_2002.csv                            -> curated dataset matching the documented variable
#                                                   list, used below
#   Unutzer_2002.xlsx                           -> same data as the .csv, Excel format (not used)


def load(file_path=RAW_DATASETS_DIR / "31_Unützer_2002" / "Unutzer_2002.csv"):
    return pd.read_csv(file_path)
