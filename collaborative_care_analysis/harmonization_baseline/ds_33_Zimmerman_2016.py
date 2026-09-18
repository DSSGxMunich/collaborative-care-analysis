import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["sex"] = map_with_check(
        series=harmonized_df["Sex"],
        mapping={
            "female": "Female",
            "Male": "Male",
        },
    ).astype("category")
    harmonized_df["age"] = harmonized_df["Age"]

    harmonized_df["country"] = "Germany"
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "age",
            "country",
            "sex",
            "follow_up_months",
        ]
    ]
