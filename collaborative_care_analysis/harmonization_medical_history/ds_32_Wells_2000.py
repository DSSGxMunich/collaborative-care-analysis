import pandas as pd

from collaborative_care_analysis.utils import map_with_check

_YES_NO = {0: "no", 1: "yes"}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # CHRONDIS = number of chronic (physical) conditions (0-11).
    harmonized_df["number_of_chronic_conditions"] = pd.to_numeric(
        harmonized_df["CHRONDIS"], errors="raise"
    ).astype("Int64")

    # CIDI baseline psychiatric history.
    harmonized_df["has_comorbid_anxiety_disorder"] = map_with_check(harmonized_df["ANX"], _YES_NO)
    harmonized_df["has_lifetime_depression"] = map_with_check(harmonized_df["LIFEDEP"], _YES_NO)
    harmonized_df["has_recurrent_major_depression"] = map_with_check(
        harmonized_df["RECMJDEP"], _YES_NO
    )

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "number_of_chronic_conditions",
            "has_comorbid_anxiety_disorder",
            "has_lifetime_depression",
            "has_recurrent_major_depression",
        ]
    ]
