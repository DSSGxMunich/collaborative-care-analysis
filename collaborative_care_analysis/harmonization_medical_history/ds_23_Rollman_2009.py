import pandas as pd

from collaborative_care_analysis.utils import map_with_check

# All baseline comorbidity flags (time-invariant; from load()'s static columns).
# CHF_0 carries a "2" for a few patients (severity grade), also treated as "yes".
_YES_NO = {0: "no", 1: "yes", 2: "yes"}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["has_hypertension"] = map_with_check(harmonized_df["HPT_0"], _YES_NO)
    harmonized_df["has_diabetes"] = map_with_check(harmonized_df["DM_0"], _YES_NO)
    harmonized_df["has_hyperlipidemia"] = map_with_check(harmonized_df["HLD_0"], _YES_NO)
    harmonized_df["has_stroke"] = map_with_check(harmonized_df["CVA_0"], _YES_NO)
    harmonized_df["has_chronic_obstructive_pulmonary_disease"] = map_with_check(
        harmonized_df["COPD_0"], _YES_NO
    )
    harmonized_df["has_renal_disease"] = map_with_check(harmonized_df["Renal_0"], _YES_NO)
    harmonized_df["has_history_of_heart_attack"] = map_with_check(harmonized_df["MI_0"], _YES_NO)
    harmonized_df["has_heart_failure_diagnosis"] = map_with_check(harmonized_df["CHF_0"], _YES_NO)

    harmonized_df["number_of_chronic_conditions"] = pd.to_numeric(
        harmonized_df["LTCn_0"], errors="raise"
    ).astype("Int64")

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_hypertension",
            "has_diabetes",
            "has_hyperlipidemia",
            "has_stroke",
            "has_chronic_obstructive_pulmonary_disease",
            "has_renal_disease",
            "has_history_of_heart_attack",
            "has_heart_failure_diagnosis",
            "number_of_chronic_conditions",
        ]
    ]
