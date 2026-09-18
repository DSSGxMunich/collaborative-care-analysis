import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["age"] = pd.to_numeric(harmonized_df["Aage"], errors="raise")

    harmonized_df["sex"] = map_with_check(
        harmonized_df["SEX"],
        {"M": "Male", "F": "Female"},
    ).astype("category")

    # ----------------------------------------------------
    # Race: Q5 race + Q4 Hispanic/Latino, one checkbox column per option,
    # respondents may check more than one. Q4 is strictly an ethnicity
    # question, not one of the Q5 race options, but we fold it in here as
    # just another checkbox to produce a single combined race/ethnicity
    # column, matching the common harmonized format used elsewhere.
    # ----------------------------------------------------
    race_cols = ["A5_5", "A5_3", "A5_2", "A5_1", "A5_4", "A5_6", "A4"]

    for col in race_cols:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")
        assert harmonized_df[col].isin([0, 1]).all(), f"{col}: unexpected values"

    def compute_race(row):
        if row[race_cols].sum() > 1:
            return "Mixed/Multiple"
        if row["A5_5"] == 1:
            return "White"
        if row["A5_3"] == 1:
            return "Black/African American"
        if row["A5_2"] == 1:
            return "Asian"
        if row["A5_1"] == 1:
            return "American Indian/Alaska Native"
        if row["A5_4"] == 1:
            return "Native Hawaiian/Pacific Islander"
        if row["A5_6"] == 1:
            return "Other"
        if row["A4"] == 1:
            return "Hispanic/Latino"
        return pd.NA

    harmonized_df["race"] = harmonized_df.apply(compute_race, axis=1).astype("string")
    harmonized_df["country"] = "USA"
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "age",
            "sex",
            "country",
            "race",
        ]
    ]
