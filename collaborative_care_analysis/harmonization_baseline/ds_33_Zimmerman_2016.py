import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["sex"] = map_with_check(
        series=harmonized_df["Sex"],
        mapping={
            "female": "Female",
            "Male": "Male",
        },
        label="sex",
    )
    harmonized_df["age"] = harmonized_df["Age"]

    harmonized_df["patientsample"] = harmonized_df["patientsample"].astype("string").str.strip()

    harmonized_df["patient_sample"] = map_with_check(
        series=harmonized_df["patientsample"],
        mapping={
            "medication NOT inclusion criteria": "Medication NOT inclusion criterion",
            "medication part of inclusion criteria": "Medication part of inclusion criterion",
        },
        label="patient_sample",
    )

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "age",
            "sex",
            "patient_sample",
            "follow_up_months",
        ]
    ]
