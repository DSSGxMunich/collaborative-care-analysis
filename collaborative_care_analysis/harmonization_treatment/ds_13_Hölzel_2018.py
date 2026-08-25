import pandas as pd


def harmonize_treatment(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # all rows that were in the intervention group had a care manager involved
    # an individual with extensive experience in healthcare
    harmonized_df["is_care_manager_involved"] = harmonized_df["study_arm"].map(
        {
            "control": "no",
            "intervention": "yes",
        }
    )

    # all rows that were in the intervention group had a physician with board certification in psychotherapy or psychology, or a psychotherapist/psychologist involved
    harmonized_df["is_psychotherapist_or_psychologist_involved_(supervisor)"] = harmonized_df[
        "study_arm"
    ].map(
        {
            "control": "no",
            "intervention": "yes",
        }
    )

    # all rows that were in the intervention group had psycheducation (about the symptoms and course of the disease, drugs, side effects, etc.)

    harmonized_df["is_psychoeducation_provided"] = harmonized_df["study_arm"].map(
        {
            "control": "no",
            "intervention": "yes",
        }
    )

    # all rows that were in the intervention group had relapse prevention provided
    harmonized_df["is_relapse_prevention_provided"] = harmonized_df["study_arm"].map(
        {
            "control": "no",
            "intervention": "yes",
        }
    )

    # all rows that were in the intervention group got activity structuring
    harmonized_df["is_activity_structuring_provided"] = harmonized_df["study_arm"].map(
        {
            "control": "no",
            "intervention": "yes",
        }
    )
    # all rows that were in the intervention group got problem-solving training
    harmonized_df["is_problem_solving_training_provided"] = harmonized_df["arm"].map(
        {
            "control": "no",
            "intervention": "yes",
        }
    )

    # all rows that were in the intervention group had initial contact in person
    harmonized_df["initial_contact_mode"] = harmonized_df["study_arm"].map(
        {
            "control": pd.NA,
            "intervention": "in_person",
        }
    )

    # all rows that were in the intervention group had follow-up contact by telephone
    harmonized_df["follow_up_contact_mode"] = harmonized_df["study_arm"].map(
        {
            "control": pd.NA,
            "intervention": "by_telephone",
        }
    )

    # return the harmonized dataset which has only the values we want
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "study_arm",
            "follow_up_months",
            "is_psychotherapist_or_psychologist_involved_(supervisor)",
            "is_care_manager_involved",
            "is_psychoeducation_provided",
            "is_relapse_prevention_provided",
            "is_activity_structuring_provided",
            "is_problem_solving_training_provided",
            "initial_contact_mode",
            "follow_up_contact_mode",
        ]
    ]
