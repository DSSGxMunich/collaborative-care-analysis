import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

OUTCOME_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months", "scl20_mean"]


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Unützer 2002 (IMPACT).

    Primary outcome: SCL-20 depression severity (mean of 20 items, 0-4).
    """
    harmonized_df = df.copy()
    harmonized_df["scl20_mean"] = pd.to_numeric(harmonized_df["scl20_mean"], errors="raise")
    return harmonized_df[OUTCOME_COLS]
