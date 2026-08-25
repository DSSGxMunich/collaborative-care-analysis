import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # -------------------------
    # Cluster assignment
    # -------------------------
    harmonized_df["cluster"] = map_with_check(
        series=harmonized_df["Cluster"],
        mapping={
            0: "No",
            1: "Yes",
        },
        label="cluster",
    )

    # -------------------------
    # Sex
    # -------------------------
    harmonized_df["sex"] = map_with_check(
        series=harmonized_df["Sex"],
        mapping={
            0: "Female",
            1: "Male",
        },
        label="sex",
    )

    # -------------------------
    # Country
    # -------------------------
    harmonized_df["country"] = map_with_check(
        series=harmonized_df["country"],
        mapping={
            0: "US",
            1: "Other",
        },
        label="country",
    )

    # -------------------------
    # Recruitment method
    # -------------------------
    harmonized_df["recruitment_method"] = map_with_check(
        series=harmonized_df["recruitmentmethod"],
        mapping={
            0: "Referral",
            1: "Systematic identification",
            2: "Referral + Systematic identification",
        },
        label="recruitment_method",
    )

    # -------------------------
    # Patient sample
    # -------------------------
    harmonized_df["patient_sample"] = map_with_check(
        series=harmonized_df["patientsample"],
        mapping={
            0: "Medication NOT inclusion criterion",
            1: "Medication part of inclusion criterion",
        },
        label="patient_sample",
    )

    # -------------------------
    # Allocation concealment
    # -------------------------
    harmonized_df["allocation_concealment"] = map_with_check(
        series=harmonized_df["allocationconcealment"],
        mapping={
            0: "Low risk of bias",
            1: "High risk of bias",
        },
        label="allocation_concealment",
    )

    # -------------------------
    # Final harmonized output
    # -------------------------
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "cluster",
            "sex",
            "country",
            "recruitment_method",
            "patient_sample",
            "allocation_concealment",
            "follow_up_months",
        ]
    ]
