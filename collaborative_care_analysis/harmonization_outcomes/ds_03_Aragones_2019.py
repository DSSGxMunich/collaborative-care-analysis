import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

HSCL_COLS = [
    "HSCLTOT",
    "HSCL_2",
]

OUTCOME_COLS = ID_COLS + HSCL_COLS

RENAME_MAP = {
    "HSCLTOT": "hscl_total",
    "HSCL_2": "hscl_suicidal",
}


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Aragones 2019."""

    harmonized_df = df[OUTCOME_COLS].copy()

    return harmonized_df.rename(
        columns=RENAME_MAP,
        errors="raise",
    )
