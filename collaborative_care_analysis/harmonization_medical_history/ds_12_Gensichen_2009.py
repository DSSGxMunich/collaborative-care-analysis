import pandas as pd

from collaborative_care_analysis.utils import map_with_check

# Baseline-only ICD-10-chapter comorbidity checklist (from the T0 chart
# review). The codebook documents these as "0/1 (nein/ja)", but the raw
# export never actually contains an explicit 0 - only 1 or blank (e.g.
# Endokrin: {NA: 396, 1: 227} across the 623 baseline rows). Checkbox-style:
# a baseline blank means "not present", not "unknown". These columns exist
# only in the T0 file, so the other three waves are blank for a different
# reason -- see harmonize().
_ICD_CHAPTER_FLAG_COLS = {
    "Endokrin": "has_endocrine_or_metabolic_condition",  # ICD Gruppe E
    "Kreislau": "has_circulatory_condition",  # ICD Gruppe I
    "Atmung": "has_respiratory_condition",  # ICD Gruppe J
    "MuskelSk": "has_musculoskeletal_condition",  # ICD Gruppe M
    "InfektNe": "has_infectious_or_neoplastic_condition",  # ICD Gruppe A-D
    # ICD Gruppe G,H,K,L,N,Q,R,S,T (nervous system, eye/ear, digestive,
    # skin, genitourinary, congenital, symptoms/signs, injury, external
    # causes) - everything not already covered by the six other chapters.
    "Sonstige": "has_other_condition_group",
    # ICD Gruppe F (psychiatric). NOT redundant with this trial's own
    # depression diagnosis/PHQ-9: only ~33% of patients carry this flag, far
    # below the near-100% expected if it just re-recorded the depression
    # that made everyone eligible for the trial. Most likely captures
    # additional/comorbid psychiatric diagnoses - not confirmed against the
    # published paper, which doesn't discuss this specific checklist item.
    "Psych": "has_other_psychiatric_condition",
}

_YES_NO = {1: "yes"}

# Unlike the seven flags above, these two genuinely use 0 as a real value
# (e.g. KHAufVor: {0: 472, 1: 71, NA: 80}) -- missing means truly unknown,
# not "no", so no fillna here. Both are patient-reported (not chart-review)
# and the codebook flags them "CAVE Recall bias" -- a self-reported,
# retrospective recall, not verified against the clinical record.
_HISTORY_FLAG_COLS = {
    "Psychiat": "had_psychiatric_treatment_before_study",
    # Codebook label: "...Depressionsbasiert..." - this is specifically a
    # depression/psychiatric-related hospitalization, not an all-cause one.
    "KHAufVor": "had_depression_related_hospitalization_before_study",
}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # The checklist is filled in once, at the T0 chart review, and the loader
    # does not broadcast it, so every follow-up row is blank by design. Only a
    # blank at baseline means "not present"; filling the follow-up blanks as
    # well would record a negative finding for a visit that never asked.
    is_baseline = harmonized_df["follow_up_months"] == 0

    for raw, harmonized in _ICD_CHAPTER_FLAG_COLS.items():
        flag = map_with_check(harmonized_df[raw], _YES_NO)
        harmonized_df[harmonized] = flag.mask(is_baseline, flag.fillna("no"))

    for raw, harmonized in _HISTORY_FLAG_COLS.items():
        harmonized_df[harmonized] = map_with_check(
            harmonized_df[raw],
            {0: "no", 1: "yes"},
        )

    # Anz_Diag = "Anzahl Diagnosen - somatische" (count of somatic
    # diagnoses), fully populated at baseline, range 0-16. Confirmed against
    # the published paper (Gensichen et al. 2009, Ann Intern Med
    # 151:369-378): "We determined the number of physical comorbid
    # conditions by counting the documented diagnoses from different
    # diagnostic groups... excluding all psychiatric diagnoses in the
    # patient record."
    harmonized_df["number_of_somatic_diagnoses"] = pd.to_numeric(
        harmonized_df["Anz_Diag"], errors="raise"
    )

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_endocrine_or_metabolic_condition",
            "has_circulatory_condition",
            "has_respiratory_condition",
            "has_musculoskeletal_condition",
            "has_infectious_or_neoplastic_condition",
            "has_other_condition_group",
            "has_other_psychiatric_condition",
            "had_psychiatric_treatment_before_study",
            "had_depression_related_hospitalization_before_study",
            "number_of_somatic_diagnoses",
        ]
    ]
