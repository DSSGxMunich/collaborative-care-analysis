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

    # Add empty study identifier column
    harmonized_df["STUDY_ID"] = pd.NA

    # Rename variables
    harmonized_df = harmonized_df.rename(columns=COLUMN_RENAME_MAP)

    # Harmonize education
    if "education_level" in harmonized_df.columns:
        harmonized_df["education_level"] = harmonized_df["education_level"].replace(
            {
                "Kein Schulabschluss": "No school degree",
                "Volks- oder Hauptschulabschluss": "Basic secondary school",
                "Mittlere Reife / Realschulabschluss": "Intermediate secondary school",
                "(Fach-) Hochschulreife": "Higher education entrance qualification",
                "Abgeschlossenes (Fach-) Hochschulstudium": "University degree",
                "Other": "Other",
            }
        )

    # Harmonize employment status
    if "employment_status" in harmonized_df.columns:
        harmonized_df["employment_status"] = harmonized_df["employment_status"].replace(
            {
                "Arbeiter/-in": "Manual worker",
                "Angestellte/-r": "Employee",
                "Beamte/-r": "Civil servant",
                "Selbstständige/-r": "Self-employed",
                "Arbeitslos": "Unemployed",
                "Berentet/ pensioniert/ Vorruhestand/ erwerbsunfähig": "Retired / disability",
                "Hausfrau/ Hausmann": "Homemaker",
                "Other": "Other",
            }
        )

    # Harmonize employment extent
    if "employment_extent" in harmonized_df.columns:
        harmonized_df["employment_extent"] = harmonized_df["employment_extent"].replace(
            {
                "Vollzeit": "Full-time",
                "Teilzeit, mindestens halbtags": "Part-time (≥50%)",
                "Teilzeit, weniger als halbtags": "Part-time (<50%)",
            }
        )

    # Harmonize financial adequacy
    if "perceived_financial_adequacy" in harmonized_df.columns:
        harmonized_df["perceived_financial_adequacy"] = harmonized_df[
            "perceived_financial_adequacy"
        ].replace(
            {
                "ja": "Yes, sufficient",
                "es geht so": "Moderate",
                "nein, schlecht": "No, insufficient",
            }
        )

    # Harmonize study center
    if "study_center" in harmonized_df.columns:
        harmonized_df["study_center"] = harmonized_df["study_center"].replace(
            {
                1: "Freiburg",
                2: "Hamburg",
            }
        )

    # Harmonize sex
    if "sex" in harmonized_df.columns:
        harmonized_df["sex"] = (
            harmonized_df["sex"]
            .astype("string")
            .str.strip()
            .replace(
                {
                    "weiblich": "female",
                    "männlich": "male",
                }
            )
        )

    # Select baseline variables (only columns that actually exist)
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
        "intervention_cluster",
        "practice_id",
        "follow_up_months",
    ]

    missing = [c for c in baseline_columns if c not in harmonized_df.columns]
    if missing:
        print(f"Warning: these expected columns are missing and will be skipped: {missing}")

    return harmonized_df[[c for c in baseline_columns if c in harmonized_df.columns]]
