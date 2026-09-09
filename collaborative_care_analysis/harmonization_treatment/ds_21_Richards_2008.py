import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # ``Group``: 1 = intervention (collaborative care); 0 = patient-randomised
    # control and -1 = cluster-randomised control -- both mapped to "control".
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["Group"],
        {-1: "control", 0: "control", 1: "intervention"},
    )

    return harmonized_df[["STUDY_ID", "patient_id", "study_arm", "follow_up_months"]]
