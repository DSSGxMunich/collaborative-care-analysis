import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()  # harmonized_df

    # The comorbidity checklist ("CDI" columns in the raw questionnaire) was
    # only asked at baseline. By the time this dataframe reaches harmonize(),
    # load()'s reshape to long format has already stripped the "B1" timepoint
    # prefix, so these columns arrive as "GI_CDI_<n>" - populated only where
    # follow_up_months == 0, and NaN at the 6- and 12-month follow-ups
    # because the checklist simply wasn't "reasked" then :D
    german_yes_no_map = {"Ja": "yes", "Nein": "no"}

    harmonized_df["has_angina"] = map_with_check(
        harmonized_df["GI_CDI_1"], german_yes_no_map, "GI_CDI_1"
    )
    harmonized_df["has_heart_failure"] = map_with_check(
        harmonized_df["GI_CDI_2"], german_yes_no_map, "GI_CDI_2"
    )
    harmonized_df["has_had_myocardial_infarction"] = map_with_check(
        harmonized_df["GI_CDI_3"], german_yes_no_map, "GI_CDI_3"
    )
    harmonized_df["has_asthma_bronchitis_or_emphysema"] = map_with_check(
        harmonized_df["GI_CDI_4"], german_yes_no_map, "GI_CDI_4"
    )
    harmonized_df["has_arthritis"] = map_with_check(
        harmonized_df["GI_CDI_5"], german_yes_no_map, "GI_CDI_5"
    )
    harmonized_df["has_osteoporosis"] = map_with_check(
        harmonized_df["GI_CDI_6"], german_yes_no_map, "GI_CDI_6"
    )
    harmonized_df["has_had_bone_fracture"] = map_with_check(
        harmonized_df["GI_CDI_7"], german_yes_no_map, "GI_CDI_7"
    )
    harmonized_df["has_had_joint_replacement"] = map_with_check(
        harmonized_df["GI_CDI_8"], german_yes_no_map, "GI_CDI_8"
    )
    harmonized_df["has_joint_stiffening"] = map_with_check(
        harmonized_df["GI_CDI_9"], german_yes_no_map, "GI_CDI_9"
    )
    harmonized_df["has_had_amputation"] = map_with_check(
        harmonized_df["GI_CDI_10"], german_yes_no_map, "GI_CDI_10"
    )
    harmonized_df["has_parkinsons_disease"] = map_with_check(
        harmonized_df["GI_CDI_11"], german_yes_no_map, "GI_CDI_11"
    )
    harmonized_df["has_had_stroke"] = map_with_check(
        harmonized_df["GI_CDI_12"], german_yes_no_map, "GI_CDI_12"
    )
    harmonized_df["has_sleep_disorder"] = map_with_check(
        harmonized_df["GI_CDI_13"], german_yes_no_map, "GI_CDI_13"
    )
    harmonized_df["has_chronic_pain_syndrome"] = map_with_check(
        harmonized_df["GI_CDI_14"], german_yes_no_map, "GI_CDI_14"
    )
    harmonized_df["has_cancer"] = map_with_check(
        harmonized_df["GI_CDI_15"], german_yes_no_map, "GI_CDI_15"
    )
    harmonized_df["has_diabetes"] = map_with_check(
        harmonized_df["GI_CDI_16"], german_yes_no_map, "GI_CDI_16"
    )
    harmonized_df["has_glaucoma"] = map_with_check(
        harmonized_df["GI_CDI_17"], german_yes_no_map, "GI_CDI_17"
    )
    harmonized_df["has_cataract"] = map_with_check(
        harmonized_df["GI_CDI_18"], german_yes_no_map, "GI_CDI_18"
    )

    # return the harmonized dataset which has only the values we want
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_angina",
            "has_heart_failure",
            "has_had_myocardial_infarction",
            "has_asthma_bronchitis_or_emphysema",
            "has_arthritis",
            "has_osteoporosis",
            "has_had_bone_fracture",
            "has_had_joint_replacement",
            "has_joint_stiffening",
            "has_had_amputation",
            "has_parkinsons_disease",
            "has_had_stroke",
            "has_sleep_disorder",
            "has_chronic_pain_syndrome",
            "has_cancer",
            "has_diabetes",
            "has_glaucoma",
            "has_cataract",
        ]
    ]
