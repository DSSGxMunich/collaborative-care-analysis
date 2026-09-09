import pandas as pd

from collaborative_care_analysis.utils import map_with_check

_YES_NO_STR = {"Yes": "yes", "No": "no"}
# "." = not assessed for most patients (268/329) - PTSD wasn't part of the
# core screen. Treated as missing, not "no".
_YES_NO_STR_WITH_DOT_MISSING = {"Yes": "yes", "No": "no", ".": pd.NA}

# Physical comorbidities, from the loader's collapsed PHYS_COMORBIDS column
# (semicolon-joined condition names per patient; NA for the 42/329 patients
# the sheet doesn't cover - kept as NA here too, not "no", per the loader's
# own note that absence could mean "not assessed").
# Names reused from ds_05/ds_08/ds_23/ds_25 for the same conditions. Cancer
# and arthritis subtypes combined into one flag each, same as ds_25 - no
# dataset here distinguishes them anyway.
_SINGLE_CONDITION_COLS = {
    "Hypertension": "has_hypertension",
    "Diabetes": "has_diabetes",
    "Hyperlipidemia": "has_hyperlipidemia",
    "Chronic Obstructive Pulmonary Disease": "has_chronic_obstructive_pulmonary_disease",
    "Asthma": "has_asthma",
    "Coronary Artery Disease": "has_coronary_heart_disease",
    "Myocardial Infarction": "has_history_of_heart_attack",
    "Congestive Heart Failure": "has_heart_failure_diagnosis",
    "Stroke/TIA": "has_history_of_stroke_or_transient_ischemic_attack",
    "Alcohol Abuse": "has_history_of_alcohol_abuse",
    "Substance Abuse": "has_history_of_other_substance_abuse",
    "Other Psychiatric Diagnosis": "has_other_psychiatric_condition",
}
_CANCER_CATEGORIES = ["History of Cancer", "Active Cancer", "Skin Cancer (Non-Melanoma)"]
_ARTHRITIS_CATEGORIES = ["Osteoarthritis/Arthritis", "Rheumatoid Arthritis"]

# Psychiatric intake diagnoses, from PARTICIPANTS (PRIME-MD). Checked against
# Rollman 2016 Table 1: disorder_GAD (154) and disorder_depression (279) both
# match the paper's counts exactly - confirms disorder_depression, not
# disorder_major_depressive, is behind the "Major depression" row.
#
# disorder_depression vs disorder_major_depressive aren't duplicates: per the
# codebook, one is "MDD or partial remission, no dysthymia", the other is
# "MDD or dysthymia". Kept both.
#
# disorder_ocd is one combined diagnosis here, unlike ds_25's separate
# obsessive/compulsive symptom screens - different instrument, not renamed
# to match.
_PSYCH_DIAGNOSIS_COLS = {
    "disorder_GAD": ("has_generalized_anxiety_disorder", _YES_NO_STR),
    "disorder_panic": ("has_panic_disorder", _YES_NO_STR),
    "disorder_depression": ("has_major_depression_or_partial_remission", _YES_NO_STR),
    "disorder_major_depressive": ("has_major_depression_or_dysthymia", _YES_NO_STR),
    "disorder_social_phobia": ("has_social_phobia", _YES_NO_STR),
    "disorder_ocd": ("has_obsessive_compulsive_disorder", _YES_NO_STR),
    "disorder_ptsd": ("has_post_traumatic_stress_disorder", _YES_NO_STR_WITH_DOT_MISSING),
}


def _has_any(names_col: pd.Series, categories: list[str]) -> pd.Series:
    # Seed from the first category's real result, not an all-NA placeholder --
    # NA | False stays NA forever, so an NA seed would never resolve to False.
    result = names_col.str.contains(categories[0], regex=False, na=pd.NA)
    for category in categories[1:]:
        result = result | names_col.str.contains(category, regex=False, na=pd.NA)
    return result


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    for raw_category, new_col in _SINGLE_CONDITION_COLS.items():
        present = harmonized_df["phys_comorbid_name"].str.contains(
            raw_category, regex=False, na=pd.NA
        )
        harmonized_df[new_col] = present.map({True: "yes", False: "no"})

    harmonized_df["has_cancer"] = _has_any(
        harmonized_df["phys_comorbid_name"], _CANCER_CATEGORIES
    ).map({True: "yes", False: "no"})
    harmonized_df["has_arthritis"] = _has_any(
        harmonized_df["phys_comorbid_name"], _ARTHRITIS_CATEGORIES
    ).map({True: "yes", False: "no"})

    for raw_col, (new_col, mapping) in _PSYCH_DIAGNOSIS_COLS.items():
        harmonized_df[new_col] = map_with_check(harmonized_df[raw_col], mapping)

    harmonized_df["number_of_chronic_conditions"] = pd.to_numeric(
        harmonized_df["n_phys_comorbids"], errors="raise"
    ).astype("Int64")

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            *_SINGLE_CONDITION_COLS.values(),
            "has_cancer",
            "has_arthritis",
            *[new_col for new_col, _ in _PSYCH_DIAGNOSIS_COLS.values()],
            "number_of_chronic_conditions",
        ]
    ]
