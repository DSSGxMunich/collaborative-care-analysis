import pandas as pd

from collaborative_care_analysis.utils import map_with_check

# GebJahr is a two-digit birth year (e.g. 43 for 1943), not age -- confirmed
# against gebdatum, which agrees on the year for 99%+ of patients. Age is
# derived as (baseline survey date) - gebdatum instead, coalescing whichever
# of these baseline-visit date columns was recorded, then broadcasting the
# result from the baseline row to the patient's other visit rows.
_BASELINE_DATE_COLS = ["PHQBeDat", "Befragun", "PHQ2BDat"]

# gebdatum disagreed across visits for these patients (see the loader's own
# warning); the true birth date is unknown, so age is left missing rather
# than trusting either recorded value.
_CONFLICTING_GEBDATUM_PATIENT_IDS = {1611, 5401, 5502, 5604, 6605}


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

    baseline_date = pd.Series(pd.NaT, index=harmonized_df.index, dtype="datetime64[ns]")
    for col in _BASELINE_DATE_COLS:
        baseline_date = baseline_date.fillna(harmonized_df[col])

    age = (baseline_date - harmonized_df["gebdatum"]).dt.days / 365.25
    conflicting = harmonized_df["patient_id"].isin(_CONFLICTING_GEBDATUM_PATIENT_IDS)
    harmonized_df["age"] = age.where(~conflicting)
    harmonized_df["age"] = harmonized_df.groupby("patient_id")["age"].transform(
        lambda s: s.ffill().bfill()
    )

    harmonized_df["sex"] = map_with_check(
        pd.to_numeric(harmonized_df["Sex"], errors="coerce"),
        {
            1.0: "Female",
            2.0: "Male",
        },
    ).astype("category")

    harmonized_df["height"] = pd.to_numeric(harmonized_df["Groesse"], errors="raise")

    harmonized_df["smoking_status"] = map_with_check(
        harmonized_df["Raucher_"],
        {
            0.0: "Never smoked",
            1.0: "Current smoker",
            2.0: "Former smoker (<1 year)",
            3.0: "Former smoker (≥1 year)",
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
