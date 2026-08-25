import pandas as pd


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Praxis ID
    harmonized_df["practice_id"] = harmonized_df["PR_ID"]

    # Patient status
    harmonized_df["patient_status"] = harmonized_df["PAT_STAT"].map(
        {
            1.0: "Known",
            2.0: "New + PHQ",
            3.0: "New + PHQ missing",
            4.0: "None",
        }
    )

    # Dates
    harmonized_df["birth_date"] = pd.to_datetime(harmonized_df["Gebdatum"], errors="coerce")
    harmonized_df["survey_date"] = pd.to_datetime(harmonized_df["Befragun"], errors="coerce")

    # Birth year
    harmonized_df["birth_year"] = pd.to_numeric(harmonized_df["GebJahr"], errors="coerce")

    # Age estimation (prefer birth date, fallback to birth year)
    if harmonized_df["birth_date"].notna().any():
        harmonized_df["age"] = (
            (harmonized_df["survey_date"] - harmonized_df["birth_date"]).dt.days / 365.25
        ).astype("float")
    else:
        harmonized_df["age"] = harmonized_df["survey_date"].dt.year - harmonized_df["birth_year"]

    # Sex
    harmonized_df["sex"] = (
        harmonized_df["Sex"]
        .map(
            {
                1.0: "Female",
                2.0: "Male",
            }
        )
        .astype("string")
    )

    # Anthropometrics
    harmonized_df["height_cm"] = pd.to_numeric(harmonized_df["Groesse"], errors="coerce")
    harmonized_df["weight_kg"] = pd.to_numeric(harmonized_df["Gewicht"], errors="coerce")

    # Smoking
    harmonized_df["smoking_status"] = harmonized_df["Raucher_"].map(
        {
            1.0: "Smoker",
            2.0: "Non-smoker",
        }
    )

    # Marital status
    harmonized_df["marital_status"] = harmonized_df["FamStand"].map(
        {
            1.0: "Single",
            2.0: "Married, living together",
            3.0: "Married, Separated",
            4.0: "Divorced",
            5.0: "Widowed",
        }
    )

    # Education
    harmonized_df["education_level"] = harmonized_df["Schulab"].map(
        {
            1.0: "No degree",
            2.0: "Basic secondary school",
            3.0: "Intermediate secondary school",
            4.0: "Higher education entrance qualification",
            5.0: "General higher education entrance qualification",
            6.0: "Other",
        }
    )

    # Living relatives
    harmonized_df["number_of_living_parents"] = pd.to_numeric(
        harmonized_df["Eltern"], errors="coerce"
    )
    harmonized_df["number_of_living_siblings"] = pd.to_numeric(
        harmonized_df["Geschw"], errors="coerce"
    )
    harmonized_df["number_of_living_children"] = pd.to_numeric(
        harmonized_df["Kinder"], errors="coerce"
    )

    # Ethnicity
    harmonized_df["ethnicity"] = harmonized_df["Ethnie"].map(
        {
            1.0: "Caucasian",
            2.0: "Asian",
            3.0: "African",
            4.0: "African-American",
            5.0: "Latino-American",
            6.0: "Other",
        }
    )

    # Insurance
    harmonized_df["insurance_type"] = harmonized_df["Vers_Sta"].map(
        {
            1.0: "GKV (public)",
            2.0: "PKV (private)",
        }
    )
    harmonized_df["insurance_provider"] = harmonized_df["Name_KV"].astype("string")

    # Employment
    harmonized_df["employment_status"] = harmonized_df["Erwerb"].map(
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
        }
    )

    # Employment-related dates
    harmonized_df["unemployed_since"] = pd.to_datetime(harmonized_df["Arblos"], errors="coerce")
    harmonized_df["temporary_disability_pension_since"] = pd.to_datetime(
        harmonized_df["EMaZ"], errors="coerce"
    )
    harmonized_df["permanent_disability_pension_since"] = pd.to_datetime(
        harmonized_df["EMaD"], errors="coerce"
    )

    # Final output (STUDY_ID added upstream)
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
