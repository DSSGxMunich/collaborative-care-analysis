import pandas as pd

from collaborative_care_analysis.utils import map_with_check

# All fields here are time-invariant (baseline; from the static columns kept by
# load()). The CODIACS cohort is defined by a recent acute coronary syndrome.
_YES_NO = {0: "no", 1: "yes"}

# acstype: type of index ACS event.
_ACS_TYPE = {
    1: "unstable_angina",
    2: "non_st_elevation_myocardial_infarction",
    3: "st_elevation_myocardial_infarction",
    4: "bundle_branch_block_or_uncertain_type_myocardial_infarction",
}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["has_diabetes"] = map_with_check(harmonized_df["diabetes_mhc"], _YES_NO)
    harmonized_df["has_renal_disease"] = map_with_check(harmonized_df["renal"], _YES_NO)

    harmonized_df["has_reduced_left_ventricular_ejection_fraction"] = map_with_check(
        harmonized_df["lvef_lt45"],
        {-2: pd.NA, -1: pd.NA, 0: "no", 1: "yes"},
    )

    harmonized_df["charlson_comorbidity_index"] = pd.to_numeric(
        harmonized_df["charlson_"], errors="raise"
    )

    harmonized_df["index_acute_coronary_syndrome_type"] = map_with_check(
        harmonized_df["acstype"], _ACS_TYPE
    ).astype("string")

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_diabetes",
            "has_renal_disease",
            "has_reduced_left_ventricular_ejection_fraction",
            "charlson_comorbidity_index",
            "index_acute_coronary_syndrome_type",
        ]
    ]
