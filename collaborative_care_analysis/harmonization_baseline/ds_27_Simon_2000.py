import pandas as pd


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Map Sex: 0 = Female, 1 = Male
    harmonized_df["sex"] = harmonized_df["Sex"].map({0: "Female", 1: "Male"}).astype("string")

    # Convert Age to numeric
    harmonized_df["age"] = pd.to_numeric(harmonized_df["Age"], errors="coerce")

    # follow_up_months provided by the loader
    harmonized_df["follow_up_months"] = df["follow_up_months"]

    # Final harmonized output (STUDY_ID added upstream)
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "age",
            "sex",
            "follow_up_months",
        ]
    ]
