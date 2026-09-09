import pandas as pd

from collaborative_care_analysis.utils import map_with_check

_YES_NO_BOOL = {True: "yes", False: "no"}
_YES_NO_STR = {"Yes": "yes", "No": "no"}

# Physical comorbidities, from the loader's pivot of the PHYS_COMORBIDS chart-
# abstraction sheet. Column names reused from existing medical_history
# clusters for the same construct (ds_05_Bekelman_2015, ds_08_Coventry_2015,
# ds_12_Gensichen_2009, ds_23_Rollman_2009 -- also a Rollman trial). "Stroke/
# TIA" is a single combined raw category here, matching ds_05's own combined
# "has_history_of_stroke_or_transient_ischemic_attack" exactly (both sources
# can't separate stroke from TIA). "History of Cancer" and "Current Cancer"
# are two separate raw categories, combined into one has_cancer flag since no
# existing dataset in this repo distinguishes active vs. past cancer either.
# Same for "Osteoarthritis" and "Rheumatoid Arthritis" into has_arthritis.
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
    "Alcohol Abuse": "has_history_of_alcohol_abuse",
    "Substance Abuse": "has_history_of_other_substance_abuse",
    "Other Psychiatric Diagnosis": "has_other_psychiatric_condition",
}

# Psychiatric intake diagnoses, from the PARTICIPANTS sheet ("Determined
# Using Primary Care Evaluation of Mental Disorders" per Table 1 of Rollman
# et al. 2018, JAMA Psychiatry 75:56-64). Verified against that Table 1 by
# overall N: disorder_major_depression 597, disorder_gad 313, disorder_panic
# 160 all reproduce the published counts exactly. disorder_obsessive and
# disorder_compulsive are two separate PRIME-MD screening items (obsessive
# thoughts vs. compulsive behaviors), not a single OCD diagnosis, so they are
# kept as two distinct columns rather than combined. acute vs. chronic PTSD
# are also kept separate -- more granular than ds_05_Bekelman_2015's single
# has_history_of_post_traumatic_stress_disorder, which the source data there
# doesn't distinguish either way, so that name isn't reused here.
_PSYCH_DIAGNOSIS_COLS = {
    "disorder_gad": "has_generalized_anxiety_disorder",
    "disorder_panic": "has_panic_disorder",
    "disorder_anxiety_nos": "has_anxiety_disorder_not_otherwise_specified",
    "disorder_major_depression": "has_major_depression_diagnosis",
    "disorder_minor_depression": "has_minor_depression_diagnosis",
    "disorder_dysthymia": "has_dysthymia",
    "disorder_social_phobia": "has_social_phobia",
    "disorder_obsessive": "has_obsessive_symptoms",
    "disorder_compulsive": "has_compulsive_symptoms",
    "disorder_acute_ptsd": "has_acute_ptsd",
    "disorder_chronic_ptsd": "has_chronic_ptsd",
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

    harmonized_df["number_of_chronic_conditions"] = pd.to_numeric(
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
            "number_of_chronic_conditions",
        ]
    ]
