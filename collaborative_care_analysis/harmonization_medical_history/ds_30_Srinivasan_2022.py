import pandas as pd

from collaborative_care_analysis.utils import map_with_check

# countchron4 / bloodpress4 are collected at baseline only (month-0 row (column names have the _0 suffix stripped)
# after the wide->long reshape); broadcast to every visit row per patient.
_BASELINE_ONLY = ["countchron4", "bloodpress4"]

_BP_CATEGORY = {
    0: "normal",
    1: "elevated",
    2: "stage_1_hypertension",
    3: "stage_2_hypertension",
}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    for col in _BASELINE_ONLY:
        harmonized_df[col] = harmonized_df.groupby("patient_id")[col].transform(
            lambda s: s.ffill().bfill()
        )

    # Number of the four cardiometabolic conditions counted by HOPE
    # (hypertension, hyperlipidaemia, diabetes, angina).
    harmonized_df["number_of_cardiometabolic_conditions"] = pd.to_numeric(
        harmonized_df["countchron4"], errors="raise"
    ).astype("Int64")

    harmonized_df["blood_pressure_category"] = map_with_check(
        harmonized_df["bloodpress4"], _BP_CATEGORY
    ).astype("string")

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "number_of_cardiometabolic_conditions",
            "blood_pressure_category",
        ]
    ]
