import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # -------------------------
    # Rename raw variables
    # -------------------------
    rename_dict = {
        "gender": "sex",
        "dem_smoke": "smoking_status",
        "dem_ed": "education_level",
        "dem_wrk": "employment_status",
        "dem_rel": "marital_status",
        "dem_inc": "income_level",
        "scr_crgvr": "has_caregiver",
        "scr_snf": "lives_in_facility",
        "scr_tele": "has_telephone_access",
        "timept": "follow_up_months",  # inherited from loader — DO NOT MAP
        "crf_sa": "has_alcohol_abuse_history",
        "crf_sao": "has_other_substance_abuse_history",
        "schfi04": "physical_activity_frequency",
        "ins_priv": "has_health_insurance",
    }
    harmonized_df = harmonized_df.rename(columns=rename_dict)

    if "has_health_insurance" in harmonized_df.columns:
        harmonized_df["has_health_insurance"] = (
            harmonized_df["has_health_insurance"]
            .apply(lambda x: "Yes" if pd.notna(x) and str(x).strip() != "" else "No")
            .astype("string")
        )

    harmonized_df["insurance_type"] = (
        harmonized_df["has_health_insurance"]
        .apply(lambda x: "PKV (private)" if x == "Yes" else pd.NA)
        .astype("string")
    )
    # -------------------------
    # Category mappings (strict)
    # -------------------------
    category_maps = {
        "sex": {1: "Male", 2: "Female"},
        "race": {
            1: "American Indian/Alaska Native",
            2: "Asian",
            3: "Black/African American",
            4: "Native Hawaiian/Pacific Islander",
            5: "White",
            6: "Other",
            99: pd.NA,
        },
        "smoking_status": {
            0: "Never smoked",
            1: "Current smoker",
            2: "Former smoker (<1 year)",
            3: "Former smoker (≥1 year)",
        },
        "education_level": {
            1: "No school degree",
            2: "Intermediate secondary school",
            3: "Higher education entrance qualification",
            4: "University degree",
            5: "University degree",
        },
        "income_level": {
            1: "<=20k",
            2: "20–35k",
            3: "35–50k",
            4: "50–70k",
            5: "70–100k",
            6: "100–150k",
            7: ">150k",
        },
        "has_caregiver": {0: "No", 1: "Yes"},
        "lives_in_facility": {0: "No", 1: "Yes"},
        "has_telephone_access": {0: "No", 1: "Yes"},
        "has_alcohol_abuse_history": {0: "No", 1: "Yes"},
        "has_other_substance_abuse_history": {0: "No", 1: "Yes"},
        "physical_activity_frequency": {
            1: "Never or rarely",
            2: "Sometimes",
            3: "Frequently",
            4: "Always or daily",
        },
    }

    # -------------------------
    # Apply map_with_check to all coded variables (except follow_up_months)
    # -------------------------
    for var, mapping in category_maps.items():
        if var in harmonized_df.columns:
            harmonized_df[var] = map_with_check(
                series=harmonized_df[var],
                mapping=mapping,
            ).astype("string")

    # -------------------------
    # Ensure age is numeric
    # -------------------------
    if "age" in harmonized_df.columns:
        harmonized_df["age"] = pd.to_numeric(harmonized_df["age"], errors="raise")

    # Employment extent (Full-time / Part-time only)

    if "employment_status" in harmonized_df.columns:
        harmonized_df["employment_extent"] = (
            harmonized_df["employment_status"]
            .map(
                {
                    1: "Full-time",
                    2: "Part-time",
                }
            )
            .astype("string")
        )
    if "employment_status" in harmonized_df.columns:
        harmonized_df["employment_status"] = (
            harmonized_df["employment_status"]
            .map(
                {
                    3: "Homemaker",
                    4: "Retired",
                    5: "Unemployed",
                    6: "Disabled",
                    7: "Student",
                    8: "Other",
                }
            )
            .astype("string")
        )

    if "marital_status" in harmonized_df.columns:
        harmonized_df["marital_status_raw"] = harmonized_df["marital_status"]

    harmonized_df["marital_status"] = (
        harmonized_df["marital_status_raw"]
        .map(
            {
                1: "Married",
                2: "Widowed",
                3: "Divorced",
                4: "Separated",
                5: "Single",
                6: "Single",
            }
        )
        .astype("string")
    )

    # 3. Create live_with_defacto (Yes/No)
    harmonized_df["live_with_defacto"] = (
        harmonized_df["marital_status_raw"]
        .apply(lambda x: "Yes" if x == 6 else "No")
        .astype("string")
    )

    # 4. Optional: drop raw column
    harmonized_df = harmonized_df.drop(columns=["marital_status_raw"])
    # -------------------------
    # Final output
    # -------------------------
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "age",
            "sex",
            "race",
            "smoking_status",
            "education_level",
            "employment_status",
            "employment_extent",
            "marital_status",
            "live_with_defacto",
            "income_level",
            "has_caregiver",
            "lives_in_facility",
            "has_telephone_access",
            "follow_up_months",
            "physical_activity_frequency",
            "has_health_insurance",
            "insurance_type",
        ]
    ]
