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
    ).astype("string")

    harmonized_df["ethnic"] = harmonized_df["ethnic"].astype("string")

    race_mapping_full = {
        # White group
        "White": "White",
        "British": "White",
        "Irish": "White",
        "Other white": "White",
        "Caucasian": "White",
        "Arab": "Middle Eastern/North African",
        # Black/African group
        "Black/African American": "Black/African",
        "Other black": "Black/African",
        "W&B African": "Black/African",
        "Caribbean": "Black/African",
        # Asian group
        "Asian": "Asian",
        "Indian": "Asian",
        "Pakistani": "Asian",
        "Bangladesh": "Asian",
        # Mixed / Multiple
        "White Asian": "Mixed/Multiple",
        "White & Asian": "Mixed/Multiple",
        "Other Mixed": "Mixed/Multiple",
        "Other mixed race": "Mixed/Multiple",
        # Hispanic
        "Hispanic": "Hispanic/Latino",
        "Hispanic/Latino": "Hispanic/Latino",
        # Other / Unknown
        "Other": "Other/Unknown",
        "Non-Caucasian": "Other/Unknown",
    }

    present_raw_values = set(harmonized_df["ethnic"].unique())
    race_mapping = {k: v for k, v in race_mapping_full.items() if k in present_raw_values}

    # harmonize ethnicity
    harmonized_df["race"] = map_with_check(
        harmonized_df["ethnic"],
        race_mapping,
    ).astype("string")

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
            "race",
            "accommodation",
            "employment",
        ]
    ]
