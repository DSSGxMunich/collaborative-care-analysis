import pandas as pd


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- Step 1: Keep baseline variables ---
    original_vars = [
        "studyid",
        "age",
        "gender",
        "race",
        "dem_smoke",
        "dem_ed",
        "dem_wrk",
        "dem_rel",
        "dem_inc",
        "scr_crgvr",
        "scr_snf",
        "scr_tele",
        "timept",
        "crf_sa",
        "crf_sao",
        "schfi04",
        "ins_priv",  # <-- updated here
    ]

    df = df[[v for v in original_vars if v in df.columns]]

    # --- Step 2: Rename variables ---
    rename_dict = {
        "studyid": "id",
        "gender": "sex",
        "dem_smoke": "smoking_status",
        "dem_ed": "education_level",
        "dem_wrk": "employment_status",
        "dem_rel": "marital_status",
        "dem_inc": "income_level",
        "scr_crgvr": "has_caregiver",
        "scr_snf": "lives_in_facility",
        "scr_tele": "has_telephone_access",
        "timept": "timepoint",
        "crf_sa": "alcohol_abuse_history",
        "crf_sao": "substance_abuse_history",
        "schfi04": "physical_activity_frequency",
        "ins_priv": "private_insurance",  # <-- updated here
    }

    df = df.rename(columns=rename_dict)

    # --- Step 3A: Harmonize private insurance (special case) ---
    if "private_insurance" in df.columns:
        df["private_insurance"] = (
            df["private_insurance"]
            .apply(lambda x: "Yes" if pd.notna(x) and str(x).strip() != "" else "No")
            .astype("string")
        )

    # --- Step 3B: Harmonize categorical variables safely ---
    category_maps = {
        "sex": {1: "Male", 2: "Female"},
        "race": {
            1: "American Indian/Alaska Native",
            2: "Asian",
            3: "Black/African American",
            4: "Native Hawaiian/Pacific Islander",
            5: "White",
            6: "Other",
            99: "Unknown",
        },
        "smoking_status": {0: "Never", 1: "Current", 2: "Quit <1 year", 3: "Quit ≥1 year"},
        "education_level": {
            1: "< High school",
            2: "High school graduate",
            3: "Some college",
            4: "College graduate",
            5: "Postgraduate",
        },
        "employment_status": {
            1: "Full-time",
            2: "Part-time",
            3: "Homemaker",
            4: "Retired",
            5: "Unemployed",
            6: "Disabled",
            7: "Student",
            8: "Other",
        },
        "marital_status": {
            1: "Married",
            2: "Widowed",
            3: "Divorced",
            4: "Separated",
            5: "Never married",
            6: "Living with partner",
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
        "timepoint": {1: "Baseline", 2: "3 months", 3: "6 months", 4: "12 months"},
        "alcohol_abuse_history": {0: "No", 1: "Yes"},
        "substance_abuse_history": {0: "No", 1: "Yes"},
        "physical_activity_frequency": {
            1: "Never or rarely",
            2: "Sometimes",
            3: "Frequently",
            4: "Always or daily",
        },
    }

    for var, mapping in category_maps.items():
        if var in df.columns:
            df[var] = df[var].replace(mapping).astype("string")

    # --- Step 4: Ensure age is numeric ---
    if "age" in df.columns:
        df["age"] = pd.to_numeric(df["age"], errors="coerce")

    return df
