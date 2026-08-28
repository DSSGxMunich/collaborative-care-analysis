import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # age
    harmonized_df["age"] = pd.to_numeric(harmonized_df["age"], errors="raise")

    # sex3
    harmonized_df["sex3"] = harmonized_df["sex3"].astype("string")
    harmonized_df["sex"] = map_with_check(
        harmonized_df["sex3"],
        {
            "Female": "Female",
            "Male": "Male",
        },
        label="sex",
    ).astype("string")

    # ethnic
    harmonized_df["ethnicity"] = harmonized_df["ethnic"].astype("string")

    # accommodation
    harmonized_df["accommodation"] = harmonized_df["accomodation"].astype("string")

    # employment
    harmonized_df["employment"] = harmonized_df["employment"].astype("string")

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "age",
            "sex",
            "ethnicity",
            "accommodation",
            "employment",
        ]
    ]
