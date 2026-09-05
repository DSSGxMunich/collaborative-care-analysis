import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Depression history (time-invariant, collected at baseline). No physical
    # comorbidity is available in this file.
    harmonized_df["has_previous_depression_episodes"] = map_with_check(
        harmonized_df["Episodes_depress"], {0: "no", 1: "yes"}
    )

    harmonized_df["number_of_previous_depression_episodes"] = pd.to_numeric(
        harmonized_df["N_episodes_depress"], errors="raise"
    ).astype("Int64")

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_previous_depression_episodes",
            "number_of_previous_depression_episodes",
        ]
    ]
