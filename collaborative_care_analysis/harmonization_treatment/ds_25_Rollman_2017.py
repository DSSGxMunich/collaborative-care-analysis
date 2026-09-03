import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # 3-arm trial. Descriptive arm names, aligned with the study-level
    # extra-info sheet's treatment ids (intervention_CCBT / intervention_ISG).
    #   "CCBT alone" -> guided online CBT only
    #   "CCBT+ISG"   -> guided online CBT plus a moderated internet support group
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["group"],
        {
            "Usual Care": "control",
            "CCBT alone": "intervention_CCBT",
            "CCBT+ISG": "intervention_ISG",
        },
    )

    return harmonized_df[["STUDY_ID", "patient_id", "study_arm", "follow_up_months"]]
