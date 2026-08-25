import pandas as pd


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # ----------------------------------------------------
    # Alcohol & substance abuse
    # ----------------------------------------------------
    harmonized_df["has_alcohol_abuse_history"] = harmonized_df["CRF_SA"].map(
        {
            0: "No",
            1: "Yes",
        }
    )

    harmonized_df["has_other_substance_abuse_history"] = harmonized_df["CRF_SAO"].map(
        {
            0: "No",
            1: "Yes",
        }
    )

    # ----------------------------------------------------
    # Gender
    # ----------------------------------------------------
    harmonized_df["sex"] = harmonized_df["CRF_GENDER"].map(
        {
            1: "Male",
            2: "Female",
        }
    )

    # ----------------------------------------------------
    # Race (single column)
    # ----------------------------------------------------
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

    harmonized_df["race"] = harmonized_df.apply(compute_race, axis=1)

    # ----------------------------------------------------
    # Ethnicity
    # ----------------------------------------------------
    harmonized_df["ethnicity"] = harmonized_df["CRF_ETH"].map(
        {
            1: "Hispanic",
            2: "Non-Hispanic",
        }
    )

    # ----------------------------------------------------
    # Smoking status
    # ----------------------------------------------------
    harmonized_df["smoking_status"] = harmonized_df["CRF_SMOKE"].map(
        {
            1: "Current smoker",
            2: "Former smoker (<1 year)",
            3: "Former smoker (≥1 year)",
            4: "Never smoked",
        }
    )

    # ----------------------------------------------------
    # follow_up_months comes from the loader
    # ----------------------------------------------------
    if "follow_up_months" not in harmonized_df.columns:
        raise ValueError("follow_up_months is missing from the loaded dataset.")

    # ----------------------------------------------------
    # Return harmonized dataset (STUDY_ID must already exist)
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
