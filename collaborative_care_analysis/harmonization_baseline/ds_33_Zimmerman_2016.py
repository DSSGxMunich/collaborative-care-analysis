import pandas as pd


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Cluster assignment
    harmonized_df["cluster"] = harmonized_df["Cluster"].map(
        {
            0: "No",
            1: "Yes",
        }
    )

    # Sex
    harmonized_df["sex"] = harmonized_df["Sex"].map(
        {
            0: "Female",
            1: "Male",
        }
    )

    # Country
    harmonized_df["country"] = harmonized_df["country"].map(
        {
            0: "US",
            1: "Other",
        }
    )

    # Recruitment method
    harmonized_df["recruitment_method"] = harmonized_df["recruitmentmethod"].map(
        {
            0: "Referral",
            1: "Systematic identification",
            2: "Referral + Systematic identification",
        }
    )

    # Patient sample
    harmonized_df["patient_sample"] = harmonized_df["patientsample"].map(
        {
            0: "Medication NOT inclusion criterion",
            1: "Medication part of inclusion criterion",
        }
    )

    # Allocation concealment
    harmonized_df["allocation_concealment"] = harmonized_df["allocationconcealment"].map(
        {
            0: "Low risk of bias",
            1: "High risk of bias",
        }
    )

    # Final harmonized output (STUDY_ID added upstream)
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
