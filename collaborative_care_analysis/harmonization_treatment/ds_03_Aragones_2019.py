import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    # Make a copy so that we do not modify the original dataframe
    harmonized_df = df.copy()

    # change the column that captures what treatment arm was used, that is the "GROUP" column, to study_arm and make its values consistent with naming convention
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["GROUP"],
        {
            0: "control",  # note that the 0 and 1 (meaning control and intervention) assumption here,  is a decisive assumption and not clearly stated
            1: "intervention",
        },
        "GROUP",
    )

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "study_arm",
            "follow_up_months",
        ]
    ]
