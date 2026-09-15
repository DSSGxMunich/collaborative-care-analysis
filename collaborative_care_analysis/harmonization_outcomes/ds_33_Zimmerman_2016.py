import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]


# The two Z columns are already standardised inside this study (both come
# out at mean 0.000, sd 0.999 over its 503 rows). They are not scores on any
# instrument: pooling them with another study's native scale would compare
# positions in two different distributions, and a name like "phq9_total_z"
# invites exactly that by sitting next to phq9_total. Kept, under names that
# say what they are, so instruments stay on their native scales.
RENAME_MAP = {
    # PHQ-9
    "Depression_severity": "phq9_total",
    "ZDepression_severity": "depression_severity_z_within_study",
    # Suicidality
    # TODO: confirm with Hannah how suicidality is measured
    "Suicidality": "suicidality",
    "ZSuicidality": "suicidality_z_within_study",
}

OUTCOME_COLS = ID_COLS + list(RENAME_MAP)


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Zimmerman 2016."""

    harmonized_df = df[OUTCOME_COLS].copy()

    return harmonized_df.rename(
        columns=RENAME_MAP,
        errors="raise",
    )
