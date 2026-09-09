import pandas as pd

from collaborative_care_analysis.utils import map_with_check

_YES_NO_BOOL = {True: "yes", False: "no"}
_YES_NO_STR = {"Yes": "yes", "No": "no"}

# Physical comorbidities, from the loader's pivot of the PHYS_COMORBIDS chart-
# abstraction sheet. Names match ds_05/ds_08/ds_12/ds_23 for the same
# conditions. Cancer and arthritis subtypes each combined into one flag.
_PHYSICAL_COLS = {
    "Hypertension": "has_hypertension",
    "Diabetes": "has_diabetes",
    "Hyperlipidemia": "has_hyperlipidemia",
    "Chronic Obstructive Pulmonary Disease": "has_chronic_obstructive_pulmonary_disease",
    "Asthma": "has_asthma",
    "Coronary Artery Disease": "has_coronary_heart_disease",
    "Myocardial Infarction": "has_history_of_heart_attack",
    "Congestive Heart Failure": "has_heart_failure_diagnosis",
    "Sleep Apnea": "has_sleep_apnea",
    "Alcohol Abuse": "has_alcohol_abuse_history",
    "Substance Abuse": "has_other_substance_abuse_history",
    "Other Psychiatric Diagnosis": "has_other_psychiatric_condition",
}

# disorder_obsessive/disorder_compulsive (two PRIME-MD screens) and
# disorder_acute_ptsd/disorder_chronic_ptsd are folded into one column each
# below, matching ds_24's has_obsessive_compulsive_disorder and ds_05's
# has_history_of_post_traumatic_stress_disorder - harmonization only pays
# off if datasets share columns, so matching names wins over keeping the
# finer split.
_PSYCH_DIAGNOSIS_COLS = {
    "disorder_gad": "has_generalized_anxiety_disorder",
    "disorder_panic": "has_panic_disorder",
    "disorder_anxiety_nos": "has_anxiety_disorder_not_otherwise_specified",
    "disorder_major_depression": "has_history_of_depression",
    "disorder_minor_depression": "has_minor_depression_diagnosis",
    "disorder_dysthymia": "has_dysthymia",
    "disorder_social_phobia": "has_social_phobia",
}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    for raw_col, new_col in _PHYSICAL_COLS.items():
        harmonized_df[new_col] = map_with_check(harmonized_df[raw_col], _YES_NO_BOOL)

    harmonized_df["has_cancer"] = map_with_check(
        harmonized_df["History of Cancer"] | harmonized_df["Current Cancer"], _YES_NO_BOOL
    )
    harmonized_df["has_arthritis"] = map_with_check(
        harmonized_df["Osteoarthritis"] | harmonized_df["Rheumatoid Arthritis"], _YES_NO_BOOL
    )

    for raw_col, new_col in _PSYCH_DIAGNOSIS_COLS.items():
        harmonized_df[new_col] = map_with_check(harmonized_df[raw_col], _YES_NO_STR)

    harmonized_df["has_obsessive_compulsive_disorder"] = map_with_check(
        (harmonized_df["disorder_obsessive"] == "Yes")
        | (harmonized_df["disorder_compulsive"] == "Yes"),
        _YES_NO_BOOL,
    )
    harmonized_df["has_history_of_post_traumatic_stress_disorder"] = map_with_check(
        (harmonized_df["disorder_acute_ptsd"] == "Yes")
        | (harmonized_df["disorder_chronic_ptsd"] == "Yes"),
        _YES_NO_BOOL,
    )

    # Not "chronic conditions" - the raw list has non-chronic stuff too
    # (Tobacco Use...), just a plain count.
    harmonized_df["number_of_recorded_comorbidities"] = pd.to_numeric(
        harmonized_df["phys_comorbid_count"], errors="raise"
    ).astype("Int64")

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            *_PHYSICAL_COLS.values(),
            "has_cancer",
            "has_arthritis",
            *_PSYCH_DIAGNOSIS_COLS.values(),
            "has_obsessive_compulsive_disorder",
            "has_history_of_post_traumatic_stress_disorder",
            "number_of_recorded_comorbidities",
        ]
    ]
