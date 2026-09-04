import pandas as pd

from collaborative_care_analysis.utils import map_with_check

# Age and gender are collected only in the screening/baseline survey, so after
# the wide->long stack in load() they are present on the month-0 row and missing
# on the 6/12/18-month rows. Broadcast the baseline value to every visit row for
# the patient.
_BASELINE_ONLY_COLS = ["age", "gender"]


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    for col in _BASELINE_ONLY_COLS:
        harmonized_df[col] = harmonized_df.groupby("patient_id")[col].transform(
            lambda s: s.ffill().bfill()
        )

    harmonized_df["age"] = pd.to_numeric(harmonized_df["age"], errors="raise")

    harmonized_df["sex"] = map_with_check(
        series=harmonized_df["gender"],
        mapping={0: "Male", 1: "Female", 2: "Other"},
    ).astype("string")

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "age",
            "sex",
            "follow_up_months",
        ]
    ]
