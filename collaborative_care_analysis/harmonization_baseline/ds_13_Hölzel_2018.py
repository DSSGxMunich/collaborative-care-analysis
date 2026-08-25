import pandas as pd

from collaborative_care_analysis.utils import map_with_check

COLUMN_RENAME_MAP = {
    "Alter": "age",
    "Geschlecht": "sex",
    "Bildung": "education_level",
    "Anstellung": "employment_status",
    "Erwerbsumfang": "employment_extent",
    "Geld_aureichend": "perceived_financial_adequacy",
    "v_zentrum": "study_center",
    "RG": "study_arm",
    "Cluster": "intervention_cluster",
    "PIN": "practice_id",
}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Rename variables
    harmonized_df = harmonized_df.rename(columns=COLUMN_RENAME_MAP, errors="raise")

    # Harmonize education
    harmonized_df["education_level"] = map_with_check(
        series=harmonized_df["education_level"],
        mapping={
            "Kein Schulabschluss": "No school degree",
            "Volks- oder Hauptschulabschluss": "Basic secondary school",
            "Mittlere Reife / Realschulabschluss": "Intermediate secondary school",
            "(Fach-) Hochschulreife": "Higher education entrance qualification",
            "Abgeschlossenes (Fach-) Hochschulstudium": "University degree",
            "Other": "Other",
        },
        label="education_level",
    )

    # Harmonize employment status
    harmonized_df["employment_status"] = map_with_check(
        series=harmonized_df["employment_status"],
        mapping={
            "Arbeiter/-in": "Manual worker",
            "Angestellte/-r": "Employee",
            "Beamte/-r": "Civil servant",
            "Selbstständige/-r": "Self-employed",
            "Arbeitslos": "Unemployed",
            "Berentet/ pensioniert/ Vorruhestand/ erwerbsunfähig": "Retired / disability",
            "Hausfrau/ Hausmann": "Homemaker",
            "Other": "Other",
        },
        label="employment_status",
    )

    # Harmonize employment extent
    harmonized_df["employment_extent"] = map_with_check(
        series=harmonized_df["employment_extent"],
        mapping={
            "Vollzeit": "Full-time",
            "Teilzeit, mindestens halbtags": "Part-time (≥50%)",
            "Teilzeit, weniger als halbtags": "Part-time (<50%)",
        },
        label="employment_extent",
    )

    # Harmonize financial adequacy
    harmonized_df["perceived_financial_adequacy"] = map_with_check(
        series=harmonized_df["perceived_financial_adequacy"],
        mapping={
            "ja": "Yes, sufficient",
            "es geht so": "Moderate",
            "nein, schlecht": "No, insufficient",
        },
        label="perceived_financial_adequacy",
    )

    # Harmonize study center
    harmonized_df["study_center"] = map_with_check(
        series=harmonized_df["study_center"],
        mapping={
            1: "Freiburg",
            2: "Hamburg",
        },
        label="study_center",
    )

    # Harmonize sex
    harmonized_df["sex"] = map_with_check(
        series=harmonized_df["sex"].astype("string").str.strip(),
        mapping={
            "weiblich": "female",
            "männlich": "male",
        },
        label="sex",
    )

    # Select baseline variables (STUDY_ID comes directly from the dataset)
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "age",
            "sex",
            "education_level",
            "employment_status",
            "employment_extent",
            "perceived_financial_adequacy",
            "study_center",
            "intervention_cluster",
            "practice_id",
        ]
    ]
