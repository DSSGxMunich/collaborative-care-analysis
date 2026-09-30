from loguru import logger
import pandas as pd

from collaborative_care_analysis.utils import map_with_check

_YES_NO_STR = {"Yes": "yes", "No": "no"}
# "." = not assessed (268/329 patients) - treated as missing, not "no".
_YES_NO_STR_WITH_DOT_MISSING = {"Yes": "yes", "No": "no", ".": pd.NA}

# Physical comorbidities, from the loader's collapsed PHYS_COMORBIDS column
# (semicolon-joined names; NA for the 42/329 patients not covered - kept as
# NA, not "no").
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
    "Alcohol Abuse": "has_alcohol_abuse_history",
    "Substance Abuse": "has_other_substance_abuse_history",
    "Other Psychiatric Diagnosis": "has_other_psychiatric_condition",
}
_CANCER_CATEGORIES = ["History of Cancer", "Active Cancer", "Skin Cancer (Non-Melanoma)"]
_ARTHRITIS_CATEGORIES = ["Osteoarthritis/Arthritis", "Rheumatoid Arthritis"]

# Psychiatric intake diagnoses (PARTICIPANTS, PRIME-MD). GAD (154) and
# depression (279) match Rollman 2016's Table 1 exactly.
#
# disorder_depression and disorder_major_depressive aren't duplicates -
# codebook: one excludes dysthymia, the other includes it. Kept both.
#
# disorder_depression -> has_history_of_depression and disorder_ptsd ->
# has_history_of_post_traumatic_stress_disorder to match ds_05's names for
# the same idea.
_PSYCH_DIAGNOSIS_COLS = {
    "disorder_GAD": ("has_generalized_anxiety_disorder", _YES_NO_STR),
    "disorder_panic": ("has_panic_disorder", _YES_NO_STR),
    "disorder_depression": ("has_history_of_depression", _YES_NO_STR),
    "disorder_major_depressive": ("has_major_depression_or_dysthymia", _YES_NO_STR),
    "disorder_social_phobia": ("has_social_phobia", _YES_NO_STR),
    "disorder_ocd": ("has_obsessive_compulsive_disorder", _YES_NO_STR),
    "disorder_ptsd": (
        "has_history_of_post_traumatic_stress_disorder",
        _YES_NO_STR_WITH_DOT_MISSING,
    ),
}


# phys_comorbid_when is a DE-DUPLICATED set of timings per patient, not one
# entry per condition: a patient can list 15 conditions and only 3 timings,
# and the two counts agree in 16% of rows, so no condition can be matched to
# its own timing. What the set does settle is the all-or-nothing case. A
# patient who records no diagnosis on or before enrollment had none of their
# listed conditions at baseline, so the whole roster is a follow-up finding
# and must not be read as medical history.
#
# The remaining limitation stands and is not fixable from this export: 127 of
# 287 patients with timings mix pre- and post-enrollment diagnoses, and for
# those the roster still counts conditions acquired during the trial.
_TIMING_AT_OR_BEFORE_ENROLLMENT = "On or before enrollment date"
_TIMING_AFTER_ENROLLMENT = (
    "Up to 12 months after the enrollment date",
    "Between 13 and 24 months after the enrollment date",
)


def _is_entirely_post_enrollment(when_col: pd.Series) -> pd.Series:
    """Rows whose every recorded timing falls after the enrollment date."""
    timings = when_col.dropna().astype(str).map(lambda cell: {t.strip() for t in cell.split(";")})
    has_pre = timings.map(lambda s: _TIMING_AT_OR_BEFORE_ENROLLMENT in s)
    has_post = timings.map(lambda s: any(t in s for t in _TIMING_AFTER_ENROLLMENT))
    return (~has_pre & has_post).reindex(when_col.index, fill_value=False)


def _has_any(names_col: pd.Series, categories: list[str]) -> pd.Series:
    # Seed with a real result, not NA - NA | False stays NA forever.
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

    # Not "chronic conditions" - the raw list has non-chronic stuff too
    # (Pregnancy, Tobacco Use, Bariatric Surgery...), just a plain count.
    harmonized_df["number_of_recorded_comorbidities"] = pd.to_numeric(
        harmonized_df["n_phys_comorbids"], errors="raise"
    ).astype("Int64")

    # Conditions the patient only acquired after enrollment are not baseline
    # medical history; without per-condition timing the only safe move is to
    # drop the whole roster for those patients.
    roster_cols = [
        *_SINGLE_CONDITION_COLS.values(),
        "has_cancer",
        "has_arthritis",
        "number_of_recorded_comorbidities",
    ]
    post_enrollment_only = _is_entirely_post_enrollment(harmonized_df["phys_comorbid_when"])
    if post_enrollment_only.any():
        baseline = post_enrollment_only & (harmonized_df["follow_up_months"] == 0)
        logger.warning(
            f"24_Rollman_2016: {int(baseline.sum())} patient(s) list only "
            f"post-enrollment diagnoses; their comorbidity roster is dropped "
            f"({int(post_enrollment_only.sum())} row(s))."
        )
    harmonized_df.loc[post_enrollment_only, roster_cols] = pd.NA

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            *_SINGLE_CONDITION_COLS.values(),
            "has_cancer",
            "has_arthritis",
            *[new_col for new_col, _ in _PSYCH_DIAGNOSIS_COLS.values()],
            "number_of_recorded_comorbidities",
        ]
    ]
