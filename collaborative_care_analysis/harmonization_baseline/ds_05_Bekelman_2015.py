import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # ----------------------------------------------------
    # Alcohol abuse
    # ----------------------------------------------------
    harmonized_df["CRF_SA"] = pd.to_numeric(harmonized_df["CRF_SA"], errors="raise")

    harmonized_df["has_alcohol_abuse_history"] = map_with_check(
        harmonized_df["CRF_SA"],
        {
            0: "No",
            1: "Yes",
        },
        label="has_alcohol_abuse_history",
    )

    # ----------------------------------------------------
    # Other substance abuse
    # ----------------------------------------------------
    harmonized_df["CRF_SAO"] = pd.to_numeric(harmonized_df["CRF_SAO"], errors="raise")

    harmonized_df["has_other_substance_abuse_history"] = map_with_check(
        harmonized_df["CRF_SAO"],
        {
            0: "No",
            1: "Yes",
        },
        label="has_other_substance_abuse_history",
    )

    # ----------------------------------------------------
    # Gender
    # ----------------------------------------------------
    harmonized_df["CRF_GENDER"] = pd.to_numeric(harmonized_df["CRF_GENDER"], errors="raise")

    harmonized_df["sex"] = map_with_check(
        harmonized_df["CRF_GENDER"],
        {
            1: "Male",
            2: "Female",
        },
        label="sex",
    )

    # ----------------------------------------------------
    # Race (single column)
    # ----------------------------------------------------
    race_cols = ["CRF_RAWH", "CRF_RABL", "CRF_RARAAS", "CRF_RAAI", "CRF_RAOT"]

    for col in race_cols:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")
        harmonized_df.loc[~harmonized_df[col].isin([0, 1]), col] = pd.NA

    def compute_race(row):
        if row["CRF_RAWH"] == 1:
            return "White"
        if row["CRF_RABL"] == 1:
            return "Black"
        if row["CRF_RARAAS"] == 1:
            return "Asian or Pacific Islander"
        if row["CRF_RAAI"] == 1:
            return "American Indian or Alaskan Native"
        if row["CRF_RAOT"] == 1:
            return "Other"
        return "Missing"

    harmonized_df["race"] = harmonized_df[race_cols].fillna(0).apply(compute_race, axis=1)

    # ----------------------------------------------------
    # Ethnicity
    # ----------------------------------------------------
    harmonized_df["CRF_ETH"] = pd.to_numeric(harmonized_df["CRF_ETH"], errors="raise")

    harmonized_df["ethnicity"] = map_with_check(
        harmonized_df["CRF_ETH"],
        {
            1: "Hispanic",
            2: "Non-Hispanic",
        },
        label="ethnicity",
    )

    # ----------------------------------------------------
    # Smoking status
    # ----------------------------------------------------
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

    # ----------------------------------------------------
    # follow_up_months comes from the loader (do NOT map)
    # ----------------------------------------------------
    if "follow_up_months" not in harmonized_df.columns:
        raise ValueError("follow_up_months is missing from the loaded dataset.")

    # ----------------------------------------------------
    # Final output
    # ----------------------------------------------------
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "sex",
            "race",
            "ethnicity",
            "smoking_status",
            "has_alcohol_abuse_history",
            "has_other_substance_abuse_history",
            "follow_up_months",
        ]
    ]
