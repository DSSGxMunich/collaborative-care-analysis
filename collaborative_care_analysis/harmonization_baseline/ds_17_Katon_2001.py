import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.utils import map_with_check

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

BASELINE_COLS = [
    "age",
    "gender",
]

SEX_MAPPING = {
    0: "Male",
    1: "Female",
}


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize baseline variables for Katon 2001."""

    harmonized_df = df[ID_COLS + BASELINE_COLS].copy()

    # map sex
    harmonized_df["sex"] = map_with_check(
        harmonized_df["gender"],
        SEX_MAPPING,
    ).astype("string")
    harmonized_df = harmonized_df.drop(columns=["gender"])

    # numeric age
    harmonized_df["age"] = pd.to_numeric(harmonized_df["age"], errors="raise")

    return harmonized_df
