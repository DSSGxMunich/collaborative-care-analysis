import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

# Depression severity = SCL-20 (mean of the 20 depression items of the SCL-90,
# 0-4 scale). Same construct/column name as ds_15/16/17 and ds_27 (Simon 2000).
OUTCOME_COLS = ID_COLS + ["scl20_mean"]


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Katon 2001."""
    return df[OUTCOME_COLS].copy()
