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
    "sex",
]

SEX_MAPPING = {
    "F": "Female",
    "M": "Male",
}


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize baseline variables for Katon 1995."""

    harmonized_df = df[ID_COLS + BASELINE_COLS].copy()

    # map sex
    harmonized_df["sex"] = map_with_check(
        harmonized_df["sex"],
        SEX_MAPPING,
    ).astype("category")

    # numeric age
    harmonized_df["age"] = pd.to_numeric(harmonized_df["age"], errors="raise")
    harmonized_df["country"] = "USA"
    return harmonized_df
