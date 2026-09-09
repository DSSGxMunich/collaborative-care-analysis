import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]

RENAME_MAP = {
    "depression": "phq9_total",  # "depression score, PHQ9 (0-27)"
    "anxiety": "gad7_total",  # "anxiety score, GAD7 (0-21)"
    **{f"phq{i}": f"phq9_{i}" for i in range(1, 10)},
    **{f"gad{i}": f"gad7_{i}" for i in range(1, 8)},
}


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Srinivasan 2022 (HOPE)."""
    harmonized_df = df.copy()
    for col in RENAME_MAP:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")
    return harmonized_df[ID_COLS + list(RENAME_MAP)].rename(columns=RENAME_MAP, errors="raise")
