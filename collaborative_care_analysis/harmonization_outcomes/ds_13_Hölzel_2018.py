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

PHQ9_COLS = [f"PHQ9_{item}" for item in range(1, 10)]

GAD7_COLS = [f"GAD7_{item}" for item in range(1, 8)]

EQ5D_COLS = [
    "EQ5D_Beweglichkeit",
    "EQ5D_Selbstversorgung",
    "EQ5D_AllgTaetigkeiten",
    "EQ5D_Schmerzen",
    "EQ5D_Angst_Depression",
]

COLUMN_RENAME_MAP = {
    **{f"PHQ9_{item}": f"phq{item:02d}" for item in range(1, 10)},
    **{f"GAD7_{item}": f"gad{item:02d}" for item in range(1, 8)},
    "PHQ_Summe": "phq_sum",
    "PHQ9_Schweregrad": "phq_severity_category",
    "EQ5D_Beweglichkeit": "eq5d_mobility",
    "EQ5D_Selbstversorgung": "eq5d_self_care",
    "EQ5D_AllgTaetigkeiten": "eq5d_usual_activities",
    "EQ5D_Schmerzen": "eq5d_pain_discomfort",
    "EQ5D_Angst_Depression": "eq5d_anxiety_depression",
}


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Hölzel 2018."""

    selected_columns = [
        COLNAME_STUDYID,
        "patient_id",
        "follow_up_months",
        *PHQ9_COLS,
        "PHQ_Summe",
        "PHQ9_Schweregrad",
        *GAD7_COLS,
        *EQ5D_COLS,
    ]

    harmonized_df = df[selected_columns].copy()

    # Map PHQ-9 item responses to scores from 0 to 3
    # The nullable Int64 dtype preserves missing values as pd.NA.
    for column in PHQ9_COLS:
        harmonized_df[column] = map_with_check(
            harmonized_df[column],
            PHQ_MAPPING,
            column,
        ).astype("Int64")

    # Store the supplied PHQ-9 total as a nullable integer.
    harmonized_df["PHQ_Summe"] = pd.to_numeric(
        harmonized_df["PHQ_Summe"],
        errors="raise",
    ).astype("Int64")

    # Calculate the PHQ-9 total only when all nine items are available.
    phq_sum_calculated = (
        harmonized_df[PHQ9_COLS]
        .sum(
            axis=1,
            min_count=len(PHQ9_COLS),
        )
        .astype("Int64")
    )

    # Place the calculated total after the stored total.
    calculated_position = harmonized_df.columns.get_loc("PHQ_Summe") + 1

    harmonized_df.insert(
        calculated_position,
        "phq_sum_calculated",
        phq_sum_calculated,
    )

    # Compare stored and calculated totals only when both are available.
    comparable = harmonized_df["PHQ_Summe"].notna() & harmonized_df["phq_sum_calculated"].notna()

    phq_sum_inconsistent = pd.Series(
        pd.NA,
        index=harmonized_df.index,
        dtype="boolean",
    )

    phq_sum_inconsistent.loc[comparable] = (
        harmonized_df.loc[comparable, "PHQ_Summe"]
        != harmonized_df.loc[
            comparable,
            "phq_sum_calculated",
        ]
    )

    harmonized_df.insert(
        calculated_position + 1,
        "phq_sum_inconsistent",
        phq_sum_inconsistent,
    )

    # Map EQ-5D-3L responses to scores from 1 to 3.
    for column in EQ5D_COLS:
        harmonized_df[column] = map_with_check(
            harmonized_df[column],
            EQ5D_MAPPING,
            column,
        ).astype("Int64")

    return harmonized_df.rename(
        columns=COLUMN_RENAME_MAP,
        errors="raise",
    )
