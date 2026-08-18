import numpy as np
import pandas as pd


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Rename variables
    harmonized_df = harmonized_df.rename(
        columns={
            "GI_B1_Alter": "age",
            "GI_B1_Geschlecht": "sex",
            "GI_B1_Bildung": "education_level",
            "GI_B1_Anstellung": "employment_status",
            "GI_B1_Erwerbsumfang": "employment_type",
            "GI_B1_Geld_aureichend": "financial_situation",
            "ID": "patient_id",
            "v_zentrum": "study_center",
            "Cluster": "cluster_id",
            "PIN": "practice_id",
        }
    )

    # Convert missing codes → real NaN
    harmonized_df = harmonized_df.replace({9: np.nan, 88: np.nan, 99: np.nan, 999: np.nan})

    # Harmonize using replace (NOT map)
    harmonized_df["sex"] = harmonized_df["sex"].replace({1: "Male", 2: "Female"})

    harmonized_df["education_level"] = harmonized_df["education_level"].replace(
        {
            0: "No school degree",
            1: "Basic secondary school",
            2: "Intermediate secondary school",
            3: "Higher education entrance qualification",
            4: "University degree",
            5: "Other",
        }
    )

    harmonized_df["employment_status"] = harmonized_df["employment_status"].replace(
        {
            1: "Manual worker",
            2: "Employee",
            3: "Civil servant",
            4: "Self-employed",
            5: "Unemployed / retraining",
            6: "Retired / disability",
            7: "Partial retirement",
            8: "Homemaker",
            9: "Other",
        }
    )

    harmonized_df["employment_type"] = harmonized_df["employment_type"].replace(
        {1: "Full-time", 2: "Part-time (≥50%)", 3: "Part-time (<50%)"}
    )

    harmonized_df["financial_situation"] = harmonized_df["financial_situation"].replace(
        {1: "Yes, sufficient", 2: "Moderate", 3: "No, insufficient"}
    )

    harmonized_df["study_center"] = harmonized_df["study_center"].replace(
        {1: "Freiburg", 2: "Hamburg"}
    )

    # Select only harmonized columns
    harmonized_df = harmonized_df[
        [
            "patient_id",
            "age",
            "sex",
            "education_level",
            "employment_status",
            "employment_type",
            "financial_situation",
            "study_center",
            "cluster_id",
            "practice_id",
        ]
    ]

    return harmonized_df
