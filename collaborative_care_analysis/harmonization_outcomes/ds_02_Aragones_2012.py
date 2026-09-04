import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

# Primary outcome of the INDI trial: PHQ-9, administered by a blinded phone
# interviewer at 0, 3, 6 and 12 months. The export carries the PHQ-9 total
# (``phq9_total``) and item 9 -- the suicidal-ideation item, scored 0-3
# (``phq9_9``). Individual items 1-8 are not in this export.
RAW_OUTCOME_COLS = ["phq9_total", "phq9_9"]

OUTCOME_COLS = ID_COLS + RAW_OUTCOME_COLS


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Aragonès 2012 (INDI)."""
    harmonized_df = df[OUTCOME_COLS].copy()

    for col in RAW_OUTCOME_COLS:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise").astype("Int64")

    return harmonized_df
