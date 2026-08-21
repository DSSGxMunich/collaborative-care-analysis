import pandas as pd

COLUMN_RENAME_MAP = {
    "GI_Alter": "age",
    "GI_Geschlecht": "sex",
    "GI_Bildung": "education_level",
    "GI_Anstellung": "employment_status",
    "GI_Erwerbsumfang": "employment_extent",
    "GI_Geld_aureichend": "perceived_financial_adequacy",
    "ID": "patient_id",
    "v_zentrum": "study_center",
    "RG": "study_arm",
    "Cluster": "intervention_cluster",
    "PIN": "practice_id",
}


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # ---------------------------------------------------------
    # Step 1: Rename variables
    # ---------------------------------------------------------
    harmonized_df = harmonized_df.rename(columns=COLUMN_RENAME_MAP)

    # ---------------------------------------------------------
    # Step 2: Harmonize sex
    # ---------------------------------------------------------
    if "sex" in harmonized_df.columns:
        harmonized_df["sex"] = (
            harmonized_df["sex"]
            .astype("string")
            .str.strip()
            .replace(
                {
                    "weiblich": "Female",
                    "männlich": "Male",
                }
            )
        )

    # ---------------------------------------------------------
    # Step 3: Harmonize education
    # ---------------------------------------------------------
    if "education_level" in harmonized_df.columns:
        harmonized_df["education_level"] = (
            harmonized_df["education_level"]
            .astype("string")
            .str.strip()
            .replace(
                {
                    "Kein Schulabschluss": "No school degree",
                    "Volks- oder Hauptschulabschluss": ("Basic secondary school"),
                    "Mittlere Reife / Realschulabschluss": ("Intermediate secondary school"),
                    "(Fach-) Hochschulreife": ("Higher education entrance qualification"),
                    "Abgeschlossenes (Fach-) Hochschulstudium": ("University degree"),
                    "Other": "Other",
                }
            )
        )

    # ---------------------------------------------------------
    # Step 4: Harmonize employment status
    # ---------------------------------------------------------
    if "employment_status" in harmonized_df.columns:
        harmonized_df["employment_status"] = (
            harmonized_df["employment_status"]
            .astype("string")
            .str.strip()
            .replace(
                {
                    "Arbeiter/-in": "Manual worker",
                    "Angestellte/-r": "Employee",
                    "Beamte/-r": "Civil servant",
                    "Selbstständige/-r": "Self-employed",
                    "Arbeitslos": "Unemployed",
                    "Berentet/ pensioniert/ Vorruhestand/ erwerbsunfähig": (
                        "Retired / disability"
                    ),
                    "Hausfrau/ Hausmann": "Homemaker",
                    "Other": "Other",
                }
            )
        )

    # ---------------------------------------------------------
    # Step 5: Harmonize employment extent
    # ---------------------------------------------------------
    if "employment_extent" in harmonized_df.columns:
        harmonized_df["employment_extent"] = (
            harmonized_df["employment_extent"]
            .astype("string")
            .str.strip()
            .replace(
                {
                    "Vollzeit": "Full-time",
                    "Teilzeit, mindestens halbtags": "Part-time (≥50%)",
                    "Teilzeit, weniger als halbtags": "Part-time (<50%)",
                }
            )
        )

    # ---------------------------------------------------------
    # Step 6: Harmonize perceived financial adequacy
    # ---------------------------------------------------------
    if "perceived_financial_adequacy" in harmonized_df.columns:
        harmonized_df["perceived_financial_adequacy"] = (
            harmonized_df["perceived_financial_adequacy"]
            .astype("string")
            .str.strip()
            .replace(
                {
                    "ja": "Yes, sufficient",
                    "es geht so": "Moderate",
                    "nein, schlecht": "No, insufficient",
                }
            )
        )

    # ---------------------------------------------------------
    # Step 7: Harmonize study center
    # ---------------------------------------------------------
    if "study_center" in harmonized_df.columns:
        harmonized_df["study_center"] = harmonized_df["study_center"].replace(
            {
                1: "Freiburg",
                2: "Hamburg",
            }
        )

    # ---------------------------------------------------------
    # Step 8: Ensure age is numeric
    # ---------------------------------------------------------
    if "age" in harmonized_df.columns:
        harmonized_df["age"] = pd.to_numeric(
            harmonized_df["age"],
            errors="coerce",
        )

    # ---------------------------------------------------------
    # Step 9: Ensure STUDY_ID exists
    # ---------------------------------------------------------
    if "STUDY_ID" not in harmonized_df.columns:
        harmonized_df["STUDY_ID"] = pd.NA

    # ---------------------------------------------------------
    # Step 10: Select baseline variables
    # ---------------------------------------------------------
    baseline_columns = [
        "STUDY_ID",
        "patient_id",
        "age",
        "sex",
        "education_level",
        "employment_status",
        "employment_extent",
        "perceived_financial_adequacy",
        "study_center",
        "study_arm",
        "intervention_cluster",
        "practice_id",
        "follow_up_months",
    ]

    # Keep only columns that actually exist
    baseline_columns = [column for column in baseline_columns if column in harmonized_df.columns]

    harmonized_df = harmonized_df[baseline_columns]

    return harmonized_df
