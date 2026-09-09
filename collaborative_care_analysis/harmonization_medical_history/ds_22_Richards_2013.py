import pandas as pd

from collaborative_care_analysis.utils import map_with_check

_YES_NO = {0: "no", 1: "yes"}

# Com_<letter>_HaveIt self-reported comorbidity checkboxes (see the CADET
# codebook) -> harmonized name.
COMORBIDITY_MAP = {
    "Com_a_HaveIt": "has_asthma",
    "Com_b_HaveIt": "has_lung_disease",
    "Com_c_HaveIt": "has_heart_disease",
    "Com_d_HaveIt": "has_hypertension",
    "Com_e_HaveIt": "has_diabetes",
    "Com_f_HaveIt": "has_ulcer_or_stomach_disease",
    "Com_g_HaveIt": "has_bowel_disease",
    "Com_h_HaveIt": "has_kidney_disease",
    "Com_i_HaveIt": "has_liver_disease",
    "Com_j_HaveIt": "has_anaemia_or_blood_disorder",
    "Com_k_HaveIt": "has_cancer",
    "Com_l_HaveIt": "has_nervous_system_disease",
    "Com_m_HaveIt": "has_arthritis",
    "Com_n_HaveIt": "has_back_pain",
    "Com_o_HaveIt": "has_other_mental_health_problem",
    "Com_p_HaveIt": "has_skin_disease",
    "Com_q_HaveIt": "has_hearing_or_visual_impairment",
    "Com_r_HaveIt": "has_other_medical_problem_1",
    "Com_s_HaveIt": "has_other_medical_problem_2",
}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    for raw, harmon in COMORBIDITY_MAP.items():
        harmonized_df[harmon] = map_with_check(harmonized_df[raw], _YES_NO)

    harmonized_df["has_long_term_condition"] = map_with_check(harmonized_df["LTC_0"], _YES_NO)
    harmonized_df["number_of_long_term_conditions"] = pd.to_numeric(
        harmonized_df["LTCn_0"], errors="raise"
    ).astype("Int64")

    return harmonized_df[
        ["STUDY_ID", "patient_id", "follow_up_months"]
        + list(COMORBIDITY_MAP.values())
        + ["has_long_term_condition", "number_of_long_term_conditions"]
    ]
