import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # ``treatarm``: 0 = usual care, 1 = collaborative care.
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["treatarm"],
        {0: "control", 1: "intervention"},
    )

    return harmonized_df[["STUDY_ID", "patient_id", "study_arm", "follow_up_months"]]
