import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    # Make a copy so that we do not modify the original dataframe
    harmonized_df = df.copy()

    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["trt"],
        {
            "Control": "control",
            "Intervention": "intervention",
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
        ]
    ]
