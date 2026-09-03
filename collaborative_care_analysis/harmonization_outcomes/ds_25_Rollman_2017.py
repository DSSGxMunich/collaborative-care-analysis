import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]

RENAME_MAP = {
    "promis_depression_total": "promis_depression_total",  # raw sum of 8 items
    "promis_depression_conversion": "promis_depression_tscore",  # T-score
    "phq9_total": "phq9_total",  # baseline only
}


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Rollman 2017 (OT trial).

    Primary outcome: PROMIS Depression (mental HRQoL) at 6 months.
    """
    harmonized_df = df.copy()
    for col in RENAME_MAP:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")
    return harmonized_df[ID_COLS + list(RENAME_MAP)].rename(columns=RENAME_MAP)
