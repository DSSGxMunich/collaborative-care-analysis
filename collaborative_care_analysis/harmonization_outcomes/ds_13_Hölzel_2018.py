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

    selected_columns = [
        COLNAME_STUDYID,
        "patient_id",
        "follow_up_months",
        *phq9_cols,
        "PHQ_Summe",
        "PHQ9_Schweregrad",
        *gad_cols,
        *eq5d_cols,
    ]

    harmonized_df = df[selected_columns].copy()

    # Map PHQ-9 item responses to scores from 0 to 3
    for column in phq9_cols:
     harmonized_df[column] = map_with_check(
            harmonized_df[column],
            PHQ_MAPPING,
            column,
        )

    # Calculate the total independently from the item-level responses.
    # This allows comparison with the total supplied in the dataset.
    harmonized_df["phq_sum_calculated"] = harmonized_df[
        phq9_cols
    ].sum(
        axis=1,
        min_count=9,
    )

    # Map EQ-5D-3L responses to scores from 1 to 3.
    for column in eq5d_cols:
        harmonized_df[column] = map_with_check(
            harmonized_df[column],
            EQ5D_MAPPING,
            column,
        )

    phq_rename_map = {
        **{
            f"PHQ9_{i}": f"phq{i:02d}"
            for i in range(1, 10)
        },
            "PHQ_Summe": "phq_sum",
            "PHQ9_Schweregrad": "phq_severity_category",
        }

    gad_rename_map = {
            f"GAD7_{i}": f"gad{i:02d}"
            for i in range(1, 8)
        }

    eq5d_rename_map = {
        "EQ5D_Beweglichkeit": "eq5d_mobility",
        "EQ5D_Selbstversorgung": "eq5d_self_care",
        "EQ5D_AllgTaetigkeiten": "eq5d_usual_activities",
        "EQ5D_Schmerzen": "eq5d_pain_discomfort",
        "EQ5D_Angst_Depression": "eq5d_anxiety_depression",
    }

    harmonized_df = harmonized_df.rename(
        columns={
            **phq_rename_map,
            **gad_rename_map,
            **eq5d_rename_map,
        },
        errors="raise",
    )

    phq_cols_harmonized = [
        f"phq{i:02d}"
        for i in range(1, 10)
    ]

    gad_cols_harmonized = [
        f"gad{i:02d}"
        for i in range(1, 8)
    ]

    output_columns = [
        COLNAME_STUDYID,
        "patient_id",
        "follow_up_months",
        *phq_cols_harmonized,
        "phq_sum",
        "phq_sum_calculated",
        "phq_severity_category",
        *gad_cols_harmonized,
        "eq5d_mobility",
        "eq5d_self_care",
        "eq5d_usual_activities",
        "eq5d_pain_discomfort",
        "eq5d_anxiety_depression",
    ] 

    return harmonized_df[output_columns]

