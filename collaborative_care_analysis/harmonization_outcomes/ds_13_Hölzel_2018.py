import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.utils import map_with_check

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


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Hölzel 2018."""

    # phq10 being the additional question: If you checked off any problems,
    # how difficult have these problems made it for you to do your
    # work, take care of things at home, or get along with other people?
    # column removed in data loading due to missing data
    phq9_cols = [f"GI_PHQ9_{i}" for i in range(1, 10)]
    gad_cols = [f"GI_GAD7_{i}" for i in range(1, 8)]

    # EQ-5D-3L Index, questionnaire on health-related quality of life
    eq5d_cols = [
        "GI_EQ5D_Beweglichkeit",
        "GI_EQ5D_Selbstversorgung",
        "GI_EQ5D_AllgTaetigkeiten",
        "GI_EQ5D_Schmerzen",
        "GI_EQ5D_Angst_Depression",
    ]

    harmonized_df = df[
        [
            COLNAME_STUDYID,
            "patient_id",  # patient identifier
            "follow_up_months",  # 0-screening, X-X months
            # PHQ-9 related
            *phq9_cols,  # item-level PHQ-9 scores
            "GI_PHQ9_Schweregrad",  # total PHQ09 score, measuring depression severity: remission (<5) and response (50% reduction)
            # GRAD-7, Generalized Anxiety Disorder 7-item scale
            *gad_cols,  # item-level GAD-7 scores
            # "GI_GAD7_Schweregrad", # total GAD-7 score, measuring anxiety severity
            # Depression-related behavior, modified from ludman et al., not available in the dataset.
            # RS-13, Resilience Scale
            # Not provided in the dataset
            # PSS, Problem-solving skills, not available in the dataset.
            # This method is modified from Bleich and Watzke in an unpublished manuscript.
            # EQ-5D-3L Index
            *eq5d_cols,
        ]
    ].copy()

    # Map PHQ-9 item-level scores to numeric values 0-3
    for col in phq9_cols:
        harmonized_df[col] = map_with_check(harmonized_df[col], PHQ_MAPPING, col)

    # Calculate PHQ-9 total score, only when all item-level scores are available
    # This is to compare with "GI_PHQ9_Schweregrad" which records the severity
    # descriptively and not to interpret them wrongly
    harmonized_df["phq_sum"] = harmonized_df[phq9_cols].sum(axis=1, min_count=9)

    # Map EQ-5D-3L item-level scores to numeric values 1-3
    for col in eq5d_cols:
        harmonized_df[col] = map_with_check(harmonized_df[col], EQ5D_MAPPING, col)

    # Rename EQ-5D columns
    eq5d_rename_map = {
        "GI_EQ5D_Beweglichkeit": "eq5d_mobility",
        "GI_EQ5D_Selbstversorgung": "eq5d_self_care",
        "GI_EQ5D_AllgTaetigkeiten": "eq5d_usual_activities",
        "GI_EQ5D_Schmerzen": "eq5d_pain_discomfort",
        "GI_EQ5D_Angst_Depression": "eq5d_anxiety_depression",
    }

    # Rename PHQ-9 columns
    phq_rename_map = {
        **{f"GI_PHQ9_{i}": f"phq{i:02d}" for i in range(1, 10)},
        "GI_PHQ9_Schweregrad": "phq_functional_difficulty",
    }

    # Rename GAD-7 columns
    gad_rename_map = {
        **{f"GI_GAD7_{i}": f"gad{i:02d}" for i in range(1, 8)},
    }

    harmonized_df = harmonized_df.rename(
        columns={
            **phq_rename_map,
            **gad_rename_map,
            **eq5d_rename_map,
        }
    )

    # Put columns in the order you want
    phq_cols_harmonized = [f"phq{i:02d}" for i in range(1, 10)]
    gad_cols_harmonized = [f"gad{i:02d}" for i in range(1, 8)]

    harmonized_df = harmonized_df[
        [
            COLNAME_STUDYID,
            "patient_id",
            "follow_up_months",
            *phq_cols_harmonized,
            "phq_sum",
            "phq_functional_difficulty",
            *gad_cols_harmonized,
            "eq5d_mobility",
            "eq5d_self_care",
            "eq5d_usual_activities",
            "eq5d_pain_discomfort",
            "eq5d_anxiety_depression",
        ]
    ]

    return harmonized_df
