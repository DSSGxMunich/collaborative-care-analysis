import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    # Make a copy so that we do not modify the original dataframe
    harmonized_df = df.copy()

    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["ARM"],
        {
            "Usual Care": "control",
            "Intervention": "intervention",
        },
    )

    # -------------------------------------------------------------------------
    # NURSE INVOLVEMENT
    # -------------------------------------------------------------------------
    # All patients assigned to the intervention group had a nurse involved
    # in their care.
    #
    # Control patients did not receive this intervention component.
    harmonized_df["is_nurse_involved"] = map_with_check(
        harmonized_df["ARM"],
        {
            "Usual Care": "no",
            "Intervention": "yes",
        },
    )

    # -------------------------------------------------------------------------
    # CARE MANAGER INVOLVEMENT
    # -------------------------------------------------------------------------
    # In this study the nurse coordinator played a role similar to the
    # care-manager role described in other collaborative-care studies.
    #
    # Therefore, intervention patients are coded as having a care manager
    # involved even though the study uses the title "nurse coordinator".
    harmonized_df["is_care_manager_involved"] = map_with_check(
        harmonized_df["ARM"],
        {
            "Usual Care": "no",
            "Intervention": "yes",
        },
    )

    # -------------------------------------------------------------------------
    # BASELINE DEPRESSION STATUS
    # -------------------------------------------------------------------------
    # The raw variable "depressed" identifies whether the patient was
    # depressed at baseline.
    #
    # 1 = depressed
    # 0 = not depressed
    #
    # Missing values remain missing.
    harmonized_df["was_depressed_at_baseline"] = map_with_check(
        harmonized_df["depressed"],
        {
            1: "yes",
            0: "no",
        },
    )

    # -------------------------------------------------------------------------
    # PSYCHIATRIST INVOLVEMENT
    # -------------------------------------------------------------------------
    # The intervention included psychiatric involvement/supervision.
    harmonized_df["is_psychiatrist_involved"] = map_with_check(
        harmonized_df["ARM"],
        {
            "Usual Care": "no",
            "Intervention": "yes",
        },
    )

    # -------------------------------------------------------------------------
    # CARDIOLOGIST INVOLVEMENT
    # -------------------------------------------------------------------------
    # The intervention involved a cardiologist as part of the collaborative
    # care team.
    harmonized_df["is_cardiologist_involved"] = map_with_check(
        harmonized_df["ARM"],
        {
            "Usual Care": "no",
            "Intervention": "yes",
        },
    )

    # -------------------------------------------------------------------------
    # DEPRESSION-SPECIFIC INTERVENTION COMPONENTS
    # -------------------------------------------------------------------------
    # The following components were NOT given to every intervention patient.
    #
    # They were specifically provided to patients who:
    #
    # 1. were in the intervention group
    # AND
    # 2. were depressed at baseline.
    #
    # These components include:
    # - psychoeducation
    # - behavioral activation
    # - antidepressant management training
    # - self-management education
    # - depression assessment education
    #
    # Missing values need special handling here.
    #
    # We should NOT simply write:
    #
    #     (ARM == "Intervention") & (depressed == 1)
    #
    # and then map False -> "no".
    #
    # This is because a missing ARM or depression value can cause the
    # condition to evaluate to False, even though the correct answer is
    # actually unknown.
    #
    # We therefore start every row as missing and only assign "yes" or "no"
    # when the information available allows us to make that conclusion.
    depression_component = pd.Series(
        pd.NA,
        index=harmonized_df.index,
        dtype="object",
    )

    # -------------------------------------------------------------------------
    # DEFINITELY "NO"
    # -------------------------------------------------------------------------
    # A patient definitely did NOT receive these depression-specific
    # intervention components if:
    #
    # - they were in Usual Care
    # OR
    # - they were not depressed at baseline.
    #
    # Notice that we do not need both variables to be available to conclude
    # "no" in these cases.
    #
    # Example:
    #
    # ARM = "Usual Care", depressed = missing
    #
    # We still know the answer is "no" because Usual Care patients did not
    # receive these intervention components.
    #
    # Similarly:
    #
    # ARM = missing, depressed = 0
    #
    # We still know the answer is "no" because these components were only
    # given to patients who were depressed at baseline.
    definitely_no = (harmonized_df["ARM"] == "Usual Care") | (harmonized_df["depressed"] == 0)

    depression_component.loc[definitely_no] = "no"

    # -------------------------------------------------------------------------
    # DEFINITELY "YES"
    # -------------------------------------------------------------------------
    # A patient definitely received these components only when BOTH
    # conditions are true:
    #
    # - intervention group
    # - depressed at baseline
    definitely_yes = (harmonized_df["ARM"] == "Intervention") & (harmonized_df["depressed"] == 1)

    depression_component.loc[definitely_yes] = "yes"

    # Any remaining rows stay as pd.NA.
    #
    # For example:
    #
    # ARM = "Intervention", depressed = missing
    #
    # We cannot tell whether the patient qualified for these
    # depression-specific components, so the correct value is unknown.

    # -------------------------------------------------------------------------
    # PSYCHOEDUCATION
    # -------------------------------------------------------------------------
    # Depressed intervention patients received psychoeducation.
    #
    # This included things such as:
    # - a depression educational video
    # - education about depression
    # - education related to self-assessment and management
    harmonized_df["is_psychoeducation_provided"] = depression_component

    # -------------------------------------------------------------------------
    # BEHAVIORAL ACTIVATION
    # -------------------------------------------------------------------------
    # Depressed intervention patients received behavioral activation.
    harmonized_df["is_behavioral_activation_provided"] = depression_component

    # -------------------------------------------------------------------------
    # ANTIDEPRESSANT MANAGEMENT
    # -------------------------------------------------------------------------
    # Depressed intervention patients received the antidepressant-management
    # component of the intervention.
    harmonized_df["is_antidepressant_management_training_provided"] = depression_component

    # -------------------------------------------------------------------------
    # SELF-MANAGEMENT EDUCATION
    # -------------------------------------------------------------------------
    # Depressed intervention patients received self-management education.
    harmonized_df["is_self_management_education_provided"] = depression_component

    # -------------------------------------------------------------------------
    # DEPRESSION ASSESSMENT EDUCATION
    # -------------------------------------------------------------------------
    # Depressed intervention patients received education related to
    # depression assessment.
    #
    # "assessment" is spelled with two s's here. This fixes the typo
    # identified during PR review.
    harmonized_df["is_depression_assessment_education_provided"] = depression_component

    # -------------------------------------------------------------------------
    # TELEMONITORING
    # -------------------------------------------------------------------------
    # All intervention patients received telemonitoring.
    #
    # This was not restricted only to intervention patients who were
    # depressed at baseline, so this variable depends only on study ARM.
    harmonized_df["is_telemonitoring_used"] = map_with_check(
        harmonized_df["ARM"],
        {
            "Usual Care": "no",
            "Intervention": "yes",
        },
    )

    # -------------------------------------------------------------------------
    # TELEMONITORING FREQUENCY
    # -------------------------------------------------------------------------
    # Intervention patients received telemonitoring daily.
    #
    # Usual Care did not receive telemonitoring, so frequency is not
    # applicable for those patients and is represented as missing rather
    # than assigning a frequency such as "none".
    harmonized_df["telemonitoring_frequency"] = map_with_check(
        harmonized_df["ARM"],
        {
            "Usual Care": pd.NA,
            "Intervention": "daily",
        },
    )

    # LIMITATION (discussed on 02.09.2026):
    # treatment harmonization currently only adds study_arm to the final dataset.
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "study_arm",
            "follow_up_months",
            # "is_nurse_involved",
            # "is_care_manager_involved",
            # "is_psychiatrist_involved",
            # "is_cardiologist_involved",
            # "was_depressed_at_baseline",
            # "is_psychoeducation_provided",
            # "is_behavioral_activation_provided",
            # "is_antidepressant_management_training_provided",
            # "is_self_management_education_provided",
            # "is_depression_assessment_education_provided",
            # "is_telemonitoring_used",
            # "telemonitoring_frequency",
        ]
    ]
