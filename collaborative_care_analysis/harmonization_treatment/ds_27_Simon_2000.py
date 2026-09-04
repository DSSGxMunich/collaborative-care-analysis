import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # 3-arm trial. Descriptive arm names.
    #   "Usual care"                        -> control
    #   "Feedback only, no care management" -> physician feedback on adherence /
    #        treatment response, without a care manager (a lighter intervention;
    #        the study-level extra-info sheet has no matching row for it)
    #   "Telephone care management"         -> feedback + a telephone care manager
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["group"],
        {
            "Usual care": "control",
            "Feedback only, no care management": "intervention_feedback",
            "Telephone care management": "intervention",
        },
    )

    return harmonized_df[["STUDY_ID", "patient_id", "study_arm", "follow_up_months"]]
