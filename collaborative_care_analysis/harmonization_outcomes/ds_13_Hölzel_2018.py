import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.utils import map_with_check

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

PHQ_MAPPING = {
    "Überhaupt nicht": 0,
    "an einzelnen Tagen": 1,
    "an mehr als die Hälfte der Tage": 2,
    "beinahe jeden Tag": 3,
    # Allow already-harmonized numeric values
    0: 0,
    1: 1,
    2: 2,
    3: 3,
}

EQ5D_MAPPING = {
    "Ich habe keine Probleme, herumzugehen.": 1,
    "Ich habe einige Probleme, herumzugehen.": 2,
    "Ich bin ans Bett gebunden.": 3,
    "Ich habe keine Probleme, für mich selbst zu sorgen.": 1,
    "Ich habe einige Probleme, mich selbst zu waschen/ mich anzuziehen.": 2,
    "Ich bin nicht in der Lage, mich selbst zu waschen/ anzuziehen.": 3,
    "Ich habe keine Probleme, meinen alltäglichen Aktivitäten nachzugehen.": 1,
    "Ich habe einige Probleme, meinen alltäglichen Aktivitäten nachzugehen.": 2,
    "Ich bin nicht in der Lage, meinen alltäglichen Aktivitäten nachzugehen.": 3,
    "Ich habe keine Schmerzen/ Beschwerden.": 1,
    "Ich habe mäßige Schmerzen/ Beschwerden.": 2,
    "Ich habe extreme Schmerzen/ Beschwerden.": 3,
    "Ich bin nicht ängstlich/ deprimiert.": 1,
    "Ich bin mäßig ängstlich/ deprimiert.": 2,
    "Ich bin extrem ängstlich/ deprimiert.": 3,
    # Allow already-harmonized numeric values
    1: 1,
    2: 2,
    3: 3,
}

PHQ9_COLS = [f"PHQ9_{item}" for item in range(1, 10)]

EQ5D_COLS = [
    "EQ5D_Beweglichkeit",
    "EQ5D_Selbstversorgung",
    "EQ5D_AllgTaetigkeiten",
    "EQ5D_Schmerzen",
    "EQ5D_Angst_Depression",
]

RENAME_MAP = {
    # PHQ-9
    **{f"PHQ9_{i}": f"phq9_{i}" for i in range(1, 10)},
    "PHQ_Summe": "phq9_total",
    "PHQ9_Schweregrad": "phq9_severity",
    # GAD-7
    **{f"GAD7_{i}": f"gad7_{i}" for i in range(1, 8)},
    # EQ-5D-3L
    "EQ5D_Beweglichkeit": "eq5d_mobility",
    "EQ5D_Selbstversorgung": "eq5d_self_care",
    "EQ5D_AllgTaetigkeiten": "eq5d_usual_activities",
    "EQ5D_Schmerzen": "eq5d_pain_discomfort",
    "EQ5D_Angst_Depression": "eq5d_anxiety_depression",
    "EQ5D_Gesundheitszustand": "eq5d_health_improvement",
}

OUTCOME_COLS = ID_COLS + list(RENAME_MAP)


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Hölzel 2018."""

    harmonized_df = df[OUTCOME_COLS].copy()

    # Map PHQ-9 item responses to scores from 0 to 3.
    for column in PHQ9_COLS:
        harmonized_df[column] = map_with_check(
            harmonized_df[column],
            PHQ_MAPPING,
            # column,
        ).astype("Int64")

    # Calculate PHQ-9 total only when all nine items are available.
    harmonized_df["phq9_total"] = (
        harmonized_df[PHQ9_COLS]
        .apply(pd.to_numeric, errors="raise")
        .sum(
            axis=1,
            min_count=len(PHQ9_COLS),
        )
        .astype("Int64")
    )

    # Calculate GAD-7 total only when all seven items are available.
    harmonized_df["gad7_total"] = (
        harmonized_df[GAD7_COLS]
        .apply(pd.to_numeric, errors="raise")
        .sum(
            axis=1,
            min_count=len(GAD7_COLS),
        )
        .astype("Int64")
    )

    # Map EQ-5D-3L responses to scores from 1 to 3.
    for column in EQ5D_COLS:
        harmonized_df[column] = map_with_check(
            harmonized_df[column],
            EQ5D_MAPPING,
        ).astype("Int64")

    return harmonized_df.rename(
        columns=RENAME_MAP,
        errors="raise",
    )
