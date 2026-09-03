import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # ``Group``: 0 = usual care, 1 = telephone collaborative care. Group 3 is the
    # non-randomised non-depressed comparison cohort -> no study arm.
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["Group"],
        {0: "control", 1: "intervention", 3: pd.NA},
    )

    return harmonized_df[["STUDY_ID", "patient_id", "study_arm", "follow_up_months"]]
