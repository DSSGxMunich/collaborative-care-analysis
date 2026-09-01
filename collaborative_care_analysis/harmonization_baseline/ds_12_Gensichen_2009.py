import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["patient_status"] = map_with_check(
        harmonized_df["PAT_STAT"],
        {
            1.0: "Known",
            2.0: "New + PHQ",
            3.0: "New + PHQ missing",
            4.0: pd.NA,
        },
    )

    harmonized_df["survey_date"] = pd.to_datetime(harmonized_df["Befragun"], errors="raise")
    harmonized_df["age"] = pd.to_numeric(harmonized_df["GebJahr"], errors="raise")

    harmonized_df["birth_year"] = harmonized_df["survey_date"].dt.year - harmonized_df["age"]

    harmonized_df["sex"] = map_with_check(
        pd.to_numeric(harmonized_df["Sex"], errors="coerce"),
        {
            1.0: "Female",
            2.0: "Male",
        },
    ).astype("string")

    harmonized_df["height"] = pd.to_numeric(harmonized_df["Groesse"], errors="raise")

    harmonized_df["smoking_status"] = map_with_check(
        harmonized_df["Raucher_"],
        {
            0.0: "Never",
            1.0: "Current",
            2.0: "Quit <1 year",
            3.0: "Quit ≥1 year",
        },
    )

    harmonized_df["education_level"] = map_with_check(
        harmonized_df["Schulab"],
        {
            1.0: "No school degree",
            2.0: "Basic secondary school",
            3.0: "Intermediate secondary school",
            4.0: "Higher education entrance qualification",
            5.0: "General higher education entrance qualification",
            6.0: "Other",
        },
    )

    harmonized_df["number_of_living_parents"] = pd.to_numeric(
        harmonized_df["Eltern"], errors="raise"
    )
    harmonized_df["number_of_living_siblings"] = pd.to_numeric(
        harmonized_df["Geschw"], errors="raise"
    )
    harmonized_df["number_of_living_children"] = pd.to_numeric(
        harmonized_df["Kinder"], errors="raise"
    )

    harmonized_df["race"] = map_with_check(
        harmonized_df["Ethnie"],
        {
            1.0: "White",
            2.0: "Asian",
            3.0: "Black/African",
            4.0: "Black/African",
            5.0: "Hispanic/Latino",
        },
    )

    harmonized_df["insurance_type"] = map_with_check(
        harmonized_df["Vers_Sta"],
        {
            1.0: "GKV (public)",
            2.0: "PKV (private)",
        },
    )

    harmonized_df["insurance_provider"] = harmonized_df["Name_KV"].astype("string")

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "patient_status",
            "age",
            "sex",
            "height",
            "smoking_status",
            "education_level",
            "number_of_living_parents",
            "number_of_living_siblings",
            "number_of_living_children",
            "race",
            "insurance_type",
            "insurance_provider",
            "follow_up_months",
        ]
    ]
