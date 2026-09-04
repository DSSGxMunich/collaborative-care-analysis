import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # ``allocation``: 1 = usual care, 2 = Healthlines Depression Service.
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["allocation"],
        {1: "control", 2: "intervention"},
    )

    return harmonized_df[["STUDY_ID", "patient_id", "study_arm", "follow_up_months"]]
