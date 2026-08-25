import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # ---------------------------------------------------------------------
    # Identifiers
    # ---------------------------------------------------------------------
    harmonized_df["practice_id"] = harmonized_df["PR_ID"]

    # ---------------------------------------------------------------------
    # Patient status
    # ---------------------------------------------------------------------
    harmonized_df["PAT_STAT"] = pd.to_numeric(harmonized_df["PAT_STAT"], errors="coerce")
    harmonized_df.loc[~harmonized_df["PAT_STAT"].isin([1.0, 2.0, 3.0, 4.0]), "PAT_STAT"] = pd.NA

    harmonized_df["patient_status"] = map_with_check(
        harmonized_df["PAT_STAT"],
        {
            1.0: "Known",
            2.0: "New + PHQ",
            3.0: "New + PHQ missing",
            4.0: "None",
            pd.NA: "Unknown",
        },
        label="patient_status",
    )

    # ---------------------------------------------------------------------
    # Dates
    # ---------------------------------------------------------------------
    harmonized_df["birth_date"] = pd.to_datetime(harmonized_df["Gebdatum"], errors="coerce")
    harmonized_df["survey_date"] = pd.to_datetime(harmonized_df["Befragun"], errors="coerce")
    harmonized_df["birth_year"] = pd.to_numeric(harmonized_df["GebJahr"], errors="coerce")

    if harmonized_df["birth_date"].notna().any():
        harmonized_df["age"] = (
            (harmonized_df["survey_date"] - harmonized_df["birth_date"]).dt.days / 365.25
        ).astype("float")
    else:
        harmonized_df["age"] = harmonized_df["survey_date"].dt.year - harmonized_df["birth_year"]

    # ---------------------------------------------------------------------
    # Sex
    # ---------------------------------------------------------------------
    harmonized_df["Sex"] = pd.to_numeric(harmonized_df["Sex"], errors="coerce")
    harmonized_df.loc[~harmonized_df["Sex"].isin([1.0, 2.0]), "Sex"] = pd.NA

    harmonized_df["sex"] = map_with_check(
        harmonized_df["Sex"],
        {
            1.0: "Female",
            2.0: "Male",
            pd.NA: "Unknown",
        },
        label="sex",
    ).astype("string")

    # ---------------------------------------------------------------------
    # Anthropometrics
    # ---------------------------------------------------------------------
    harmonized_df["height_cm"] = pd.to_numeric(harmonized_df["Groesse"], errors="coerce")
    harmonized_df["weight_kg"] = pd.to_numeric(harmonized_df["Gewicht"], errors="coerce")

    # ---------------------------------------------------------------------
    # Smoking
    # ---------------------------------------------------------------------
    harmonized_df["Raucher_"] = pd.to_numeric(harmonized_df["Raucher_"], errors="coerce")
    harmonized_df.loc[~harmonized_df["Raucher_"].isin([0.0, 1.0, 2.0, 3.0]), "Raucher_"] = pd.NA

    harmonized_df["smoking_status"] = map_with_check(
        harmonized_df["Raucher_"],
        {
            0.0: "Never",
            1.0: "Current",
            2.0: "Quit <1 year",
            3.0: "Quit ≥1 year",
            pd.NA: "Unknown",
        },
        label="smoking_status",
    )

    # ---------------------------------------------------------------------
    # Marital status
    # ---------------------------------------------------------------------
    harmonized_df["FamStand"] = pd.to_numeric(harmonized_df["FamStand"], errors="coerce")
    harmonized_df.loc[~harmonized_df["FamStand"].isin([1, 2, 3, 4, 5]), "FamStand"] = pd.NA

    harmonized_df["marital_status"] = map_with_check(
        harmonized_df["FamStand"],
        {
            1.0: "Single",
            2.0: "Married, living together",
            3.0: "Married, separated",
            4.0: "Divorced",
            5.0: "Widowed",
            pd.NA: "Unknown",
        },
        label="marital_status",
    )

    # ---------------------------------------------------------------------
    # Education
    # ---------------------------------------------------------------------
    harmonized_df["Schulab"] = pd.to_numeric(harmonized_df["Schulab"], errors="coerce")
    harmonized_df.loc[~harmonized_df["Schulab"].isin([1, 2, 3, 4, 5, 6]), "Schulab"] = pd.NA

    harmonized_df["education_level"] = map_with_check(
        harmonized_df["Schulab"],
        {
            1.0: "No degree",
            2.0: "Basic secondary school",
            3.0: "Intermediate secondary school",
            4.0: "Higher education entrance qualification",
            5.0: "General higher education entrance qualification",
            6.0: "Other",
            pd.NA: "Unknown",
        },
        label="education_level",
    )

    # ---------------------------------------------------------------------
    # Living relatives
    # ---------------------------------------------------------------------
    harmonized_df["number_of_living_parents"] = pd.to_numeric(
        harmonized_df["Eltern"], errors="coerce"
    )
    harmonized_df["number_of_living_siblings"] = pd.to_numeric(
        harmonized_df["Geschw"], errors="coerce"
    )
    harmonized_df["number_of_living_children"] = pd.to_numeric(
        harmonized_df["Kinder"], errors="coerce"
    )

    # ---------------------------------------------------------------------
    # Ethnicity
    # ---------------------------------------------------------------------
    harmonized_df["Ethnie"] = pd.to_numeric(harmonized_df["Ethnie"], errors="coerce")
    harmonized_df.loc[~harmonized_df["Ethnie"].isin([1, 2, 3, 4, 5, 6]), "Ethnie"] = pd.NA

    harmonized_df["ethnicity"] = map_with_check(
        harmonized_df["Ethnie"],
        {
            1.0: "Caucasian",
            2.0: "Asian",
            3.0: "African",
            4.0: "African-American",
            5.0: "Latino-American",
            6.0: "Other",
            pd.NA: "Unknown",
        },
        label="ethnicity",
    )

    # ---------------------------------------------------------------------
    # Insurance
    # ---------------------------------------------------------------------
    harmonized_df["Vers_Sta"] = pd.to_numeric(harmonized_df["Vers_Sta"], errors="coerce")
    harmonized_df.loc[~harmonized_df["Vers_Sta"].isin([1, 2]), "Vers_Sta"] = pd.NA

    harmonized_df["insurance_type"] = map_with_check(
        harmonized_df["Vers_Sta"],
        {
            1.0: "GKV (public)",
            2.0: "PKV (private)",
            pd.NA: "Unknown",
        },
        label="insurance_type",
    )

    harmonized_df["insurance_provider"] = harmonized_df["Name_KV"].astype("string")

    # ---------------------------------------------------------------------
    # Employment
    # ---------------------------------------------------------------------
    harmonized_df["Erwerb"] = pd.to_numeric(harmonized_df["Erwerb"], errors="coerce")
    harmonized_df.loc[~harmonized_df["Erwerb"].isin(range(1, 13)), "Erwerb"] = pd.NA

    harmonized_df["employment_status"] = map_with_check(
        harmonized_df["Erwerb"],
        {
            1.0: "Fully employed",
            2.0: "Part-time",
            3.0: "Vocational training",
            4.0: "Retraining",
            5.0: "Registered unemployed",
            6.0: "Parental leave",
            7.0: "Homemaker",
            8.0: "Temporary disability pension",
            9.0: "Permanent disability pension",
            10.0: "Early retirement",
            11.0: "Regular old-age retirement",
            12.0: "Survivor's/Widow's pension",
            pd.NA: "Unknown",
        },
        label="employment_status",
    )

    harmonized_df["unemployed_since"] = pd.to_datetime(harmonized_df["Arblos"], errors="coerce")
    harmonized_df["temporary_disability_pension_since"] = pd.to_datetime(
        harmonized_df["EMaZ"], errors="coerce"
    )
    harmonized_df["permanent_disability_pension_since"] = pd.to_datetime(
        harmonized_df["EMaD"], errors="coerce"
    )

    # ---------------------------------------------------------------------
    # Final output
    # ---------------------------------------------------------------------
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "practice_id",
            "patient_status",
            "birth_date",
            "survey_date",
            "birth_year",
            "age",
            "sex",
            "height_cm",
            "weight_kg",
            "smoking_status",
            "marital_status",
            "education_level",
            "number_of_living_parents",
            "number_of_living_siblings",
            "number_of_living_children",
            "ethnicity",
            "insurance_type",
            "insurance_provider",
            "employment_status",
            "unemployed_since",
            "temporary_disability_pension_since",
            "permanent_disability_pension_since",
            "follow_up_months",
        ]
    ]
