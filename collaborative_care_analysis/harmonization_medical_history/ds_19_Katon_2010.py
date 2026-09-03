import pandas as pd

from collaborative_care_analysis.utils import map_with_check

_YES_NO = {0: "no", 1: "yes"}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # TEAMcare enrolled patients with depression AND poorly controlled diabetes
    # and/or coronary heart disease. DIABETIC / HEARTDIS are baseline flags.
    harmonized_df["has_diabetes"] = map_with_check(harmonized_df["DIABETIC"], _YES_NO)
    harmonized_df["has_heart_disease"] = map_with_check(harmonized_df["HEARTDIS"], _YES_NO)

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_diabetes",
            "has_heart_disease",
        ]
    ]
