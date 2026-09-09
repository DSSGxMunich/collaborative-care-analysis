import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

OUTCOME_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months", "scl20_mean"]


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Simon 2004 (SCL-20, mean of 20 items)."""
    return df[OUTCOME_COLS].copy()
