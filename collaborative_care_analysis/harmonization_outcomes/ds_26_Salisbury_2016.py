from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]

# Both totals are sums of whole-numbered items, so a fractional value is not
# a score on either scale. This study ships only the totals, no items, so
# there is nothing to recompute them from and the rows cannot be repaired.
_WHOLE_NUMBER_SCORES = ["phq9_total", "gad7_total"]


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Salisbury 2016 (Healthlines Depression).

    Primary outcome: PHQ-9 response at 4 months (``phq9_total``). ``gad7_total``
    is a secondary anxiety measure.
    """
    harmonized_df = df.copy()
    for col in _WHOLE_NUMBER_SCORES:
        score = pd.to_numeric(harmonized_df[col], errors="raise")
        fractional = score.notna() & (score % 1 != 0)
        if fractional.any():
            logger.warning(
                f"26_Salisbury_2016 {col}: {int(fractional.sum())} non-integer "
                f"total(s) of {int(score.notna().sum())} set missing."
            )
        harmonized_df[col] = score.where(~fractional)
    return harmonized_df[ID_COLS + _WHOLE_NUMBER_SCORES]
