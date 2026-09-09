import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # 3-arm trial. ``CLNTYPE`` gives the clinic-level allocation (the binary
    # ``INTERV`` collapses the two QI arms). Descriptive names aligned with the
    # study-level extra-info sheet (intervention_Medication / intervention_Therapy).
    #   U = usual care
    #   M = QI-Meds  (nurse-supported medication management)
    #   T = QI-Therapy (access to trained local CBT psychotherapists)
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["CLNTYPE"],
        {
            "U": "control",
            "M": "intervention_Medication",
            "T": "intervention_Therapy",
        },
    )

    return harmonized_df[["STUDY_ID", "patient_id", "study_arm", "follow_up_months"]]
