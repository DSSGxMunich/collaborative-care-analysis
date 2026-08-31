import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Alcohol abuse

    harmonized_df["CRF_SA"] = pd.to_numeric(harmonized_df["CRF_SA"], errors="raise")

    harmonized_df["has_alcohol_abuse_history"] = map_with_check(
        harmonized_df["CRF_SA"],
        {
            0: "No",
            1: "Yes",
        },
        label="has_alcohol_abuse_history",
    )

    # Other substance abuse

    harmonized_df["CRF_SAO"] = pd.to_numeric(harmonized_df["CRF_SAO"], errors="raise")

    harmonized_df["has_other_substance_abuse_history"] = map_with_check(
        harmonized_df["CRF_SAO"],
        {
            0: "No",
            1: "Yes",
        },
        label="has_other_substance_abuse_history",
    )

    # Gender
    harmonized_df["CRF_GENDER"] = pd.to_numeric(harmonized_df["CRF_GENDER"], errors="raise")

    harmonized_df["sex"] = map_with_check(
        harmonized_df["CRF_GENDER"],
        {
            1: "Male",
            2: "Female",
        },
        label="sex",
    )

    # Race
    race_cols = ["CRF_RAWH", "CRF_RABL", "CRF_RARAAS", "CRF_RAAI", "CRF_RAOT"]

    for col in race_cols:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")

    harmonized_df["CRF_ETH"] = pd.to_numeric(harmonized_df["CRF_ETH"], errors="raise")

    race_code = pd.Series(0, index=harmonized_df.index)  # default Missing

    race_code = race_code.mask(harmonized_df["CRF_ETH"] == 1, 7)

    race_code = race_code.mask(harmonized_df["CRF_RAWH"] == 1, 5)
    race_code = race_code.mask(harmonized_df["CRF_RABL"] == 1, 3)
    race_code = race_code.mask(harmonized_df["CRF_RARAAS"] == 1, 2)
    race_code = race_code.mask(harmonized_df["CRF_RAAI"] == 1, 1)
    race_code = race_code.mask(harmonized_df["CRF_RAOT"] == 1, 6)

    harmonized_df["race_code"] = race_code

    race_mapping = {
        1: "American Indian/Alaska Native",
        2: "Asian or Pacific Islander",
        3: "Black/African American",
        5: "White",
        6: "Other",
        7: "Hispanic",
    }

    harmonized_df["race"] = map_with_check(
        harmonized_df["race_code"], race_mapping, label="race"
    ).astype("string")

    # Smoking status

    harmonized_df["CRF_SMOKE"] = pd.to_numeric(harmonized_df["CRF_SMOKE"], errors="raise")

    harmonized_df["smoking_status"] = map_with_check(
        harmonized_df["CRF_SMOKE"],
        {
            1: "Current smoker",
            2: "Former smoker (<1 year)",
            3: "Former smoker (≥1 year)",
            4: "Never smoked",
        },
        label="smoking_status",
    )

    if "follow_up_months" not in harmonized_df.columns:
        raise ValueError("follow_up_months is missing from the loaded dataset.")

    # Final output

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "sex",
            "race",
            "smoking_status",
            "has_alcohol_abuse_history",
            "has_other_substance_abuse_history",
            "follow_up_months",
        ]
    ]
