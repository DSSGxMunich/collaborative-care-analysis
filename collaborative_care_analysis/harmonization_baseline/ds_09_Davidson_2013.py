import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["age"] = pd.to_numeric(harmonized_df["age"], errors="raise")

    harmonized_df["sex"] = map_with_check(
        series=harmonized_df["sex"],
        mapping={1: "Male", 2: "Female"},
    ).astype("category")

    harmonized_df["country"] = "USA"
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
