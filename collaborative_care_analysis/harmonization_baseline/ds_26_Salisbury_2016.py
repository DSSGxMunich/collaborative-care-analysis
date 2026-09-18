import pandas as pd

from collaborative_care_analysis.utils import map_with_check

# Gender is collected only at baseline (``d_13_1_gender`` on the month-0 row).
# Broadcast it to every visit row for the patient. There is no continuous age
# in this dataset -- only ``age_categorical`` -- so no ``age`` column is emitted.


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    gender = harmonized_df.groupby("patient_id")["d_13_1_gender"].transform(
        lambda s: s.ffill().bfill()
    )

    harmonized_df["sex"] = map_with_check(
        gender,
        {1: "Male", 2: "Female"},
    ).astype("category")

    harmonized_df["country"] = "UK"
    return harmonized_df[["STUDY_ID", "patient_id", "follow_up_months", "sex", "country"]]
