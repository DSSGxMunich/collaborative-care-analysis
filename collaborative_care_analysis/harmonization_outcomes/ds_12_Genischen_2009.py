import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

RENAME_MAP = {
    # PHQ-9 items
    **{f"phqf{i}": f"phq9_{i}" for i in range(1, 10)},
    "PHQges": "phq9_total",

    # SF-36 health survey value
    "pfi": "sf36_physical_functioning_value",
    "rolph": "sf36_role_physical_value",
    "pain": "sf36_bodily_pain_value",
    "ghp": "sf36_general_health_value",
    "vital": "sf36_vitality_value",
    "social": "sf36_social_functioning_value",
    "rolem": "sf36_role_emotional_value",
    "mhi": "sf36_mental_health_value",    

    # EQ-5D item-level score
    "eq_f1": "eq5d_mobility",
    "eq_f2": "eq5d_self_care",
    "eq_f3": "eq5d_usual_activities",
    "eq_f4": "eq5d_pain_discomfort",
    "eq_f5": "eq5d_anxiety_depression",
    "eq_f6": "eq5d_health_improvement",

    # EQ-5D calculated dimension values
    "eq5d10": "eq5d_mobility_value",
    "eq5d20": "eq5d_self_care_value",
    "eq5d30": "eq5d_usual_activities_value",
    "eq5d40": "eq5d_pain_discomfort_value",
    "eq5d50": "eq5d_anxiety_depression_value",

}

OUTCOME_COLS = ID_COLS + list(RENAME_MAP)


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Genischen 2009."""

    harmonized_df = df[OUTCOME_COLS].copy()

    return harmonized_df.rename(
        columns=RENAME_MAP,
        errors="raise",
    )
