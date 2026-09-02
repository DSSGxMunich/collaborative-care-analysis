import pandas as pd

from collaborative_care_analysis.utils import map_with_check

SEX_MAPPING = {
    "F": "Female",
    "M": "Male",
}


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize baseline variables for Katon 1995."""

    harmonized_df = df.copy()

    # map sex
    if "sex" in harmonized_df.columns:
        harmonized_df["sex"] = map_with_check(
            harmonized_df["sex"],
            SEX_MAPPING,
        ).astype("string")

    # numeric age
    if "age" in harmonized_df.columns:
        harmonized_df["age"] = pd.to_numeric(harmonized_df["age"], errors="raise")

    return harmonized_df
