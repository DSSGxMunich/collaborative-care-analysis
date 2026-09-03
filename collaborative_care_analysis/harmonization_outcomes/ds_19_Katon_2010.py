import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

# Depression severity = SCL-20 (mean of 20 items, 0-4), already produced as
# ``scl20_mean`` by the loader. Same name as ds_14/15/16/17/18 and ds_27.
OUTCOME_COLS = ID_COLS + ["scl20_mean"]


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Katon 2010 (TEAMcare)."""
    return df[OUTCOME_COLS].copy()
