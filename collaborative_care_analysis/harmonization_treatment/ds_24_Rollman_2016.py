import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # "High Anx" = randomised at baseline; "WW" = watchful-waiting cohort,
    # randomised later only if symptoms worsened ("WW never randomized" -> no arm).
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["group"],
        {
            "High Anx UC": "control",
            "High Anx CC": "intervention",
            "WW randomized to UC": "control",
            "WW randomized to CC": "intervention",
            "WW never randomized": pd.NA,
        },
    )

    return harmonized_df[["STUDY_ID", "patient_id", "study_arm", "follow_up_months"]]
