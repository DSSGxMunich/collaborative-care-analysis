import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # ----------------------------------------------------
    # Sex (clean + strict mapping)
    # ----------------------------------------------------
    harmonized_df["Sex"] = pd.to_numeric(harmonized_df["Sex"], errors="coerce")
    harmonized_df.loc[~harmonized_df["Sex"].isin([0, 1]), "Sex"] = pd.NA

    harmonized_df["sex"] = map_with_check(
        harmonized_df["Sex"],
        {
            0: "Female",
            1: "Male",
            pd.NA: "Unknown",
        },
        label="sex",
    ).astype("string")

    # ----------------------------------------------------
    # Age (numeric)
    # ----------------------------------------------------
    harmonized_df["age"] = pd.to_numeric(harmonized_df["Age"], errors="coerce")

    # ----------------------------------------------------
    # follow_up_months (comes from loader — do NOT map)
    # ----------------------------------------------------
    harmonized_df["follow_up_months"] = df["follow_up_months"]

    # ----------------------------------------------------
    # Final harmonized output
    # ----------------------------------------------------
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "age",
            "sex",
            "follow_up_months",
        ]
    ]
