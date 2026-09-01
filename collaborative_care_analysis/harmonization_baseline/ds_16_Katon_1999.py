import pandas as pd


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["age"] = pd.to_numeric(harmonized_df["age"], errors="raise")

    harmonized_df["sex"] = harmonized_df["sex"].astype("string")

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "age",
            "sex",
        ]
    ]
