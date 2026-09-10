import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["age"] = pd.to_numeric(harmonized_df["CALAGE"], errors="raise")

    harmonized_df["sex"] = map_with_check(
        harmonized_df["FEMALE"],
        {0: "Male", 1: "Female"},
    ).astype("category")

    harmonized_df["marital_status"] = map_with_check(
        harmonized_df["MARRIED"],
        {1: "Married", 0: "Unmarried"},
    ).astype("string")

    harmonized_df["race"] = map_with_check(
        harmonized_df["S2RACEX"],
        {1: "American Indian", 2: "Asian", 3: "Black", 4: "Hispanic", 5: "White"},
    ).astype("string")

    harmonized_df["employment_status"] = map_with_check(
        harmonized_df["WORK"],
        {1: "Employed", 0: "Unemployed"},
    ).astype("string")

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "age",
            "sex",
            "marital_status",
            "race",
            "employment_status",
        ]
    ]
