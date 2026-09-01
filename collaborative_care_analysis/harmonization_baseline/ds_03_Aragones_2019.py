import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame):
    harmonized_df = df.copy()

    # rename variables
    rename_dict = {
        "AGE": "age",
        "SEX": "sex",
    }
    harmonized_df = harmonized_df.rename(columns=rename_dict)

    # map sex
    if "sex" in harmonized_df.columns:
        harmonized_df["sex"] = map_with_check(
            series=harmonized_df["sex"],
            mapping={0: "Female", 1: "Male"},
            label="sex",
        ).astype("string")

    # numeric age
    if "age" in harmonized_df.columns:
        harmonized_df["age"] = pd.to_numeric(harmonized_df["age"], errors="raise")

    # final output
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "age",
            "sex",
            "follow_up_months",
        ]
    ]
