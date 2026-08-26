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

    # ----------------------------------------------------
    # Rename variables
    # ----------------------------------------------------
    harmonized_df = harmonized_df.rename(columns=COLUMN_RENAME_MAP, errors="raise")

    # ----------------------------------------------------
    # Education level
    # ----------------------------------------------------
    harmonized_df["education_level"] = pd.to_numeric(
        harmonized_df["education_level"], errors="coerce"
    )
    harmonized_df.loc[
        ~harmonized_df["education_level"].isin([0, 1, 2, 3, 4, 5]), "education_level"
    ] = pd.NA

    numeric_education_map = {
        0: "Kein Schulabschluss",
        1: "Volks- oder Hauptschulabschluss",
        2: "Mittlere Reife / Realschulabschluss",
        3: "(Fach-) Hochschulreife",
        4: "Hochschulreife / Abitur",
        5: "Abgeschlossenes (Fach-) Hochschulstudium",
    }

    harmonized_df["education_level"] = harmonized_df["education_level"].map(numeric_education_map)

    harmonized_df["education_level"] = map_with_check(
        series=harmonized_df["education_level"],
        mapping={
            "Kein Schulabschluss": "No school degree",
            "Volks- oder Hauptschulabschluss": "Basic secondary school",
            "Mittlere Reife / Realschulabschluss": "Intermediate secondary school",
            "(Fach-) Hochschulreife": "Higher education entrance qualification",
            "Hochschulreife / Abitur": "General higher education entrance qualification",
            "Abgeschlossenes (Fach-) Hochschulstudium": "University degree",
            "Other": "Other",
        },
        label="education_level",
    )

    # ----------------------------------------------------
    # Employment status
    # ----------------------------------------------------
    harmonized_df["employment_status"] = pd.to_numeric(
        harmonized_df["employment_status"], errors="raise"
    )
    harmonized_df.loc[
        ~harmonized_df["employment_status"].isin(range(1, 13)), "employment_status"
    ] = pd.NA

    numeric_employment_status_map = {
        1: "Arbeiter/-in",
        2: "Angestellte/-r",
        3: "Beamte/-r",
        4: "Selbstständige/-r",
        5: "Arbeitslos",
        6: "Berentet/ pensioniert/ Vorruhestand/ erwerbsunfähig",
        7: "Hausfrau/ Hausmann",
        8: "Other",
        9: "Other",
        10: "Other",
        11: "Other",
        12: "Other",
    }

    harmonized_df["employment_status"] = harmonized_df["employment_status"].map(
        numeric_employment_status_map
    )

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

    # ----------------------------------------------------
    # Employment extent
    # ----------------------------------------------------
    harmonized_df["employment_extent"] = pd.to_numeric(
        harmonized_df["employment_extent"], errors="raise"
    )
    harmonized_df.loc[~harmonized_df["employment_extent"].isin([1, 2, 3]), "employment_extent"] = (
        pd.NA
    )

    numeric_employment_extent_map = {
        1: "Vollzeit",
        2: "Teilzeit, mindestens halbtags",
        3: "Teilzeit, weniger als halbtags",
    }

    harmonized_df["employment_extent"] = harmonized_df["employment_extent"].map(
        numeric_employment_extent_map
    )

    harmonized_df["employment_extent"] = map_with_check(
        series=harmonized_df["employment_extent"],
        mapping={
            "Vollzeit": "Full-time",
            "Teilzeit, mindestens halbtags": "Part-time (≥50%)",
            "Teilzeit, weniger als halbtags": "Part-time (<50%)",
        },
        label="employment_extent",
    )

    # ----------------------------------------------------
    # Financial adequacy
    # ----------------------------------------------------
    harmonized_df["perceived_financial_adequacy"] = pd.to_numeric(
        harmonized_df["perceived_financial_adequacy"], errors="raise"
    )
    harmonized_df.loc[
        ~harmonized_df["perceived_financial_adequacy"].isin([1, 2, 3]),
        "perceived_financial_adequacy",
    ] = pd.NA

    numeric_financial_map = {
        1: "ja",
        2: "es geht so",
        3: "nein, schlecht",
    }

    harmonized_df["perceived_financial_adequacy"] = harmonized_df[
        "perceived_financial_adequacy"
    ].map(numeric_financial_map)

    harmonized_df["perceived_financial_adequacy"] = map_with_check(
        series=harmonized_df["perceived_financial_adequacy"],
        mapping={
            "ja": "Yes, sufficient",
            "es geht so": "Moderate",
            "nein, schlecht": "No, insufficient",
        },
        label="perceived_financial_adequacy",
    )

    # ----------------------------------------------------
    # Study center
    # ----------------------------------------------------
    harmonized_df["study_center"] = pd.to_numeric(harmonized_df["study_center"], errors="raise")
    harmonized_df.loc[~harmonized_df["study_center"].isin([1, 2]), "study_center"] = pd.NA

    harmonized_df["study_center"] = map_with_check(
        series=harmonized_df["study_center"],
        mapping={
            1: "Freiburg",
            2: "Hamburg",
            pd.NA: "Unknown",
        },
        label="study_center",
    )

    # ----------------------------------------------------
    # Sex
    # ----------------------------------------------------
    harmonized_df["sex"] = pd.to_numeric(harmonized_df["sex"], errors="raise")
    harmonized_df.loc[~harmonized_df["sex"].isin([1, 2]), "sex"] = pd.NA

    numeric_sex_map = {
        1: "männlich",
        2: "weiblich",
    }

    harmonized_df["sex"] = harmonized_df["sex"].map(numeric_sex_map)

    harmonized_df["sex"] = map_with_check(
        series=harmonized_df["sex"],
        mapping={
            "weiblich": "female",
            "männlich": "male",
        },
        label="sex",
    )

    # ----------------------------------------------------
    # Final selection
    # ----------------------------------------------------
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
            "study_arm",
            "intervention_cluster",
            "practice_id",
        ]
    ]
