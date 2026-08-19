import numpy as np
import pandas as pd


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Convert missing codes → real NaN
    harmonized_df = harmonized_df.replace({9: np.nan, 88: np.nan, 99: np.nan, 999: np.nan})

    # Harmonize education
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
    harmonized_df["employment_status"] = harmonized_df["employment_status"].replace(
        {
            "Arbeiter/-in": "Manual worker",
            "Angestellte/-r": "Employee",
            "Beamte/-r": "Civil servant",
            "Selbstständige/-r": "Self-employed",
            "Arbeitslos": "Unemployed",
            "Berentet/ pensioniert/ Vorruhestand/ erwerbsunfähig": ("Retired / disability"),
            "Hausfrau/ Hausmann": "Homemaker",
            "Other": "Other",
        }
    )

    # Harmonize employment extent
    harmonized_df["employment_extent"] = harmonized_df["employment_extent"].replace(
        {
            "Vollzeit": "Full-time",
            "Teilzeit, mindestens halbtags": "Part-time (≥50%)",
            "Teilzeit, weniger als halbtags": "Part-time (<50%)",
        }
    )

    # Harmonize financial adequacy
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
    harmonized_df["study_center"] = harmonized_df["study_center"].replace(
        {
            1: "Freiburg",
            2: "Hamburg",
        }
    )

    # Select baseline variables
    harmonized_df = harmonized_df[
        [
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
        ]
    ]

    return harmonized_df
