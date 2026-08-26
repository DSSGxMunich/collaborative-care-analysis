import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

PHQ_COLS = [
    "Depression_severity",
    "ZDepression_severity",
]

SUICIDALITY_COLS = [
    "Suicidality",
    "ZSuicidality",
]

MEDICATION_COLS = [
    "medication_adherence",
    # TODO: confirm with Hannah about the followup month and what the value A,B entails
]

OUTCOME_COLS = ID_COLS + PHQ_COLS + SUICIDALITY_COLS + MEDICATION_COLS

RENAME_MAP = {
    # PHQ-9
    "Depression_severity": "phq9_total",
    "ZDepression_severity": "phq9_total_z",
    # Suicidality
    # TODO: confirm with Hannah how suicidality is measured
    "Suicidality": "suicidality",
    "ZSuicidality": "suicidality_z",
}


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Zimmerman 2016."""

    harmonized_df = df[OUTCOME_COLS].copy()

    return harmonized_df.rename(
        columns=RENAME_MAP,
        errors="raise",
    )
