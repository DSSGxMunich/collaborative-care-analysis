import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # -------------------------
    # Cluster assignment
    # -------------------------
    harmonized_df["Cluster"] = pd.to_numeric(harmonized_df["Cluster"], errors="coerce")
    harmonized_df.loc[~harmonized_df["Cluster"].isin([0, 1]), "Cluster"] = pd.NA

    harmonized_df["cluster"] = map_with_check(
        series=harmonized_df["Cluster"],
        mapping={
            0: "No",
            1: "Yes",
            pd.NA: "Unknown",
        },
        label="cluster",
    )

    # -------------------------
    # Sex
    # -------------------------
    harmonized_df["Sex"] = pd.to_numeric(harmonized_df["Sex"], errors="coerce")
    harmonized_df.loc[~harmonized_df["Sex"].isin([0, 1]), "Sex"] = pd.NA

    harmonized_df["sex"] = map_with_check(
        series=harmonized_df["Sex"],
        mapping={
            0: "Female",
            1: "Male",
            pd.NA: "Unknown",
        },
        label="sex",
    )

    # -------------------------
    # Country
    # -------------------------
    harmonized_df["country"] = pd.to_numeric(harmonized_df["country"], errors="coerce")
    harmonized_df.loc[~harmonized_df["country"].isin([0, 1]), "country"] = pd.NA

    harmonized_df["country"] = map_with_check(
        series=harmonized_df["country"],
        mapping={
            0: "US",
            1: "Other",
            pd.NA: "Unknown",
        },
        label="country",
    )

    # -------------------------
    # Recruitment method
    # -------------------------
    harmonized_df["recruitmentmethod"] = pd.to_numeric(
        harmonized_df["recruitmentmethod"], errors="coerce"
    )
    harmonized_df.loc[~harmonized_df["recruitmentmethod"].isin([0, 1, 2]), "recruitmentmethod"] = (
        pd.NA
    )

    harmonized_df["recruitment_method"] = map_with_check(
        series=harmonized_df["recruitmentmethod"],
        mapping={
            0: "Referral",
            1: "Systematic identification",
            2: "Referral + Systematic identification",
            pd.NA: "Unknown",
        },
        label="recruitment_method",
    )

    # -------------------------
    # Patient sample
    # -------------------------
    harmonized_df["patientsample"] = pd.to_numeric(harmonized_df["patientsample"], errors="coerce")
    harmonized_df.loc[~harmonized_df["patientsample"].isin([0, 1]), "patientsample"] = pd.NA

    harmonized_df["patient_sample"] = map_with_check(
        series=harmonized_df["patientsample"],
        mapping={
            0: "Medication NOT inclusion criterion",
            1: "Medication part of inclusion criterion",
            pd.NA: "Unknown",
        },
        label="patient_sample",
    )

    # -------------------------
    # Allocation concealment
    # -------------------------
    harmonized_df["allocationconcealment"] = pd.to_numeric(
        harmonized_df["allocationconcealment"], errors="coerce"
    )
    harmonized_df.loc[
        ~harmonized_df["allocationconcealment"].isin([0, 1]), "allocationconcealment"
    ] = pd.NA

    harmonized_df["allocation_concealment"] = map_with_check(
        series=harmonized_df["allocationconcealment"],
        mapping={
            0: "Low risk of bias",
            1: "High risk of bias",
            pd.NA: "Unknown",
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
