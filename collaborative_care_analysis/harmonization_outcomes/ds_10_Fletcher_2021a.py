import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

# Pre-computed scale totals in the Link-me export.
#   k10_score     -> K10 (Kessler-10) psychological distress, range 10-50.
#                    PRIMARY outcome (assessed at 6 months).
#   phqdep_total  -> PHQ-9 depression total, range 0-27.
#   gad_total     -> GAD-7 anxiety total, range 0-21.
RENAME_MAP = {
    "k10_score": "k10_total",
    "phqdep_total": "phq9_total",
    "gad_total": "gad7_total",
}


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Fletcher 2021a (Link-me)."""
    harmonized_df = df[ID_COLS + list(RENAME_MAP)].copy()

    for col in RENAME_MAP:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")

    return harmonized_df.rename(columns=RENAME_MAP, errors="raise")
