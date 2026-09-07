import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # 3-arm trial. Descriptive arm names, aligned with the study-level
    # extra-info sheet (intervention_TelCare / intervention_Psychotherapy).
    #   0 = usual care
    #   1 = telephone care management
    #   2 = telephone care management + structured telephone CBT
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["group"],
        {
            0: "control",
            1: "intervention_TelCare",
            2: "intervention_Psychotherapy",
        },
    )

    return harmonized_df[["STUDY_ID", "patient_id", "study_arm", "follow_up_months"]]
