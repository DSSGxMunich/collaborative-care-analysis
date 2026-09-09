import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Salisbury 2016 (Healthlines Depression).

    Primary outcome: PHQ-9 response at 4 months (``phq9_total``). ``gad7_total``
    is a secondary anxiety measure.
    """
    harmonized_df = df.copy()
    for col in ["phq9_total", "gad7_total"]:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")
    return harmonized_df[ID_COLS + ["phq9_total", "gad7_total"]]
