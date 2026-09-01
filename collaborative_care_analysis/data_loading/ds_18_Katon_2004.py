# The number of follow-up assessments for depression in the IPD do not correspond to the number of
# follow-ups described in the paper (4 vs. 3). Until this is resolved, we won't proceed with this file.

import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(file_path=RAW_DATASETS_DIR / "18_Katon_2004" / "katon2004.sav"):
    return pd.read_spss(file_path)
