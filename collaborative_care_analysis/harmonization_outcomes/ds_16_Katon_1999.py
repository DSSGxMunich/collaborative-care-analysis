import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

RENAME_MAP = {
    # SCL-20
    "avg_scl20": "scl20_total",
}

OUTCOME_COLS = ID_COLS + list(RENAME_MAP)


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Katon 1999."""

    harmonized_df = df[OUTCOME_COLS].copy()

    return harmonized_df.rename(
        columns=RENAME_MAP,
        errors="raise",
    )
