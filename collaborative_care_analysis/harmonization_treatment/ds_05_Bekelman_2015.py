import pandas as pd


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Standardize study arm
    harmonized_df["study_arm"] = harmonized_df["ARM"].map(
        {
            "Usual Care": "control",
            "Intervention": "intervention",
        }
    )

    # Nurses were involved in the intervention group
    harmonized_df["is_nurse_involved"] = harmonized_df["ARM"].map(
        {
            "Usual Care": "no",
            "Intervention": "yes",
        }
    )

    # In this study, the nurse plays a similar role to care managers
    # in other studies
    harmonized_df["is_care_manager_involved"] = harmonized_df["ARM"].map(
        {
            "Usual Care": "no",
            "Intervention": "yes",
        }
    )

    # Depression status at baseline
    harmonized_df["was_depressed_at_baseline"] = harmonized_df["depressed"].map(
        {
            1: "yes",
            0: "no",
        }
    )

    # Psychiatrist involved in the intervention group
    harmonized_df["is_psychiatrist_involved"] = harmonized_df["ARM"].map(
        {
            "Usual Care": "no",
            "Intervention": "yes",
        }
    )

    # Cardiologist involved in the intervention group
    harmonized_df["is_cardiologist_involved"] = harmonized_df["ARM"].map(
        {
            "Usual Care": "no",
            "Intervention": "yes",
        }
    )

    # These depression-specific components were only provided to patients
    # who were both in the intervention group and depressed at baseline PHQ9 > 9
    intervention_and_depressed = (harmonized_df["ARM"] == "Intervention") & (
        harmonized_df["depressed"] == 1
    )

    harmonized_df["is_psychoeducation_provided"] = intervention_and_depressed.map(
        {
            True: "yes",
            False: "no",
        }
    )

    harmonized_df["is_behavioral_activation_provided"] = intervention_and_depressed.map(
        {
            True: "yes",
            False: "no",
        }
    )

    harmonized_df["is_antidepressant_management_training_provided"] = (
        intervention_and_depressed.map(
            {
                True: "yes",
                False: "no",
            }
        )
    )

    harmonized_df["is_self_management_education_provided"] = intervention_and_depressed.map(
        {
            True: "yes",
            False: "no",
        }
    )

    harmonized_df["is_depression_assesment_education_provided"] = intervention_and_depressed.map(
        {
            True: "yes",
            False: "no",
        }
    )

    # All intervention patients received daily telemonitoring
    harmonized_df["is_telemonitoring_used"] = harmonized_df["ARM"].map(
        {
            "Usual Care": "no",
            "Intervention": "yes",
        }
    )

    harmonized_df["telemonitoring_frequency"] = harmonized_df["ARM"].map(
        {
            "Usual Care": pd.NA,
            "Intervention": "daily",
        }
    )

    # Return only harmonized treatment variables
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "study_arm",
            "follow_up_months",
            "is_nurse_involved",
            "is_care_manager_involved",
            "is_psychiatrist_involved",
            "is_cardiologist_involved",
            "was_depressed_at_baseline",
            "is_psychoeducation_provided",
            "is_behavioral_activation_provided",
            "is_antidepressant_management_training_provided",
            "is_self_management_education_provided",
            "is_depression_assesment_education_provided",
            "is_telemonitoring_used",
            "telemonitoring_frequency",
        ]
    ]
