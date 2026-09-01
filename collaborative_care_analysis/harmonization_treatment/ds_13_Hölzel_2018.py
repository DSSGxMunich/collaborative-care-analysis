import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_treatment(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # RG coding in the original dataset:
    # 0 = control
    # 1 = intervention
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["RG"],
        {
            0: "control",
            1: "intervention",
        },
    )

    # All rows that were in the intervention group had a care manager involved.
    # The care manager was an individual with extensive experience in healthcare.
    harmonized_df["is_care_manager_involved"] = map_with_check(
        harmonized_df["study_arm"],
        {
            "control": "no",
            "intervention": "yes",
        },
    )

    # All rows that were in the intervention group had a physician with
    # board certification in psychotherapy or psychology, or a
    # psychotherapist/psychologist involved as a supervisor.
    harmonized_df["is_psychotherapist_or_psychologist_involved_(supervisor)"] = map_with_check(
        harmonized_df["study_arm"],
        {
            "control": "no",
            "intervention": "yes",
        },
    )

    # All rows that were in the intervention group received psychoeducation.
    # This included education about symptoms, the course of the disease,
    # medications, side effects, etc.
    harmonized_df["is_psychoeducation_provided"] = map_with_check(
        harmonized_df["study_arm"],
        {
            "control": "no",
            "intervention": "yes",
        },
    )

    # All rows that were in the intervention group received relapse prophylaxis.
    harmonized_df["is_relapse_prophylaxis_provided"] = map_with_check(
        harmonized_df["study_arm"],
        {
            "control": "no",
            "intervention": "yes",
        },
    )

    # All rows that were in the intervention group received
    # activity structuring.
    harmonized_df["is_activity_structuring_provided"] = map_with_check(
        harmonized_df["study_arm"],
        {
            "control": "no",
            "intervention": "yes",
        },
    )

    # Problem-solving training was provided only where indicated.
    # Therefore, we should not say that every intervention patient
    # definitely received it.
    harmonized_df["problem_solving_training"] = map_with_check(
        harmonized_df["study_arm"],
        {
            "control": pd.NA,
            "intervention": "as_indicated",
        },
    )

    # The initial contact for intervention patients took place in person
    # at the doctor's practice.
    harmonized_df["initial_contact_mode"] = map_with_check(
        harmonized_df["study_arm"],
        {
            "control": pd.NA,
            "intervention": "in_person",
        },
    )

    # Subsequent contacts for intervention patients were conducted
    # by telephone.
    harmonized_df["follow_up_contact_mode"] = map_with_check(
        harmonized_df["study_arm"],
        {
            "control": pd.NA,
            "intervention": "by_telephone",
        },
    )

    # Return the harmonized dataset with only the variables we want.
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "study_arm",
            "follow_up_months",
            "is_psychotherapist_or_psychologist_involved_(supervisor)",
            "is_care_manager_involved",
            "is_psychoeducation_provided",
            "is_relapse_prophylaxis_provided",
            "is_activity_structuring_provided",
            "problem_solving_training",
            "initial_contact_mode",
            "follow_up_contact_mode",
        ]
    ]
