import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize_baseline(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # ----------------------------------------------------
    # Medication adherence (Medadh)
    # ----------------------------------------------------
    harmonized_df["Medadh"] = pd.to_numeric(harmonized_df["Medadh"], errors="raise")

    harmonized_df["medication_adherence"] = map_with_check(
        harmonized_df["Medadh"],
        {
            1.0: "Yes",
            0.0: "No",
        },
    )

    # ----------------------------------------------------
    # Suicidal thoughts (h9)
    # ----------------------------------------------------
    harmonized_df["h9"] = pd.to_numeric(harmonized_df["h9"], errors="raise")

    harmonized_df["suicidal_ideation"] = map_with_check(
        harmonized_df["h9"],
        {
            1: "Yes",
            0: "No",
            9999.0: pd.NA,
        },
    )

    # ----------------------------------------------------
    # Suicidal plan (h9a)
    # ----------------------------------------------------
    harmonized_df["h9a"] = pd.to_numeric(harmonized_df["h9a"], errors="raise")

    harmonized_df["suicidal_plan"] = map_with_check(
        harmonized_df["h9a"],
        {
            1: "Yes",
            0: "No",
            9999.0: pd.NA,
        },
    )

    # ----------------------------------------------------
    # Suicide attempt (h9b)
    # ----------------------------------------------------
    harmonized_df["h9b"] = pd.to_numeric(harmonized_df["h9b"], errors="raise")

    harmonized_df["suicide_attempt"] = map_with_check(
        harmonized_df["h9b"],
        {1: "Yes", 0: "No", 9999.0: pd.NA},
    )

    # ----------------------------------------------------
    # Long-standing illness (das_h1)
    # ----------------------------------------------------
    harmonized_df["das_h1"] = pd.to_numeric(harmonized_df["das_h1"], errors="raise")

    harmonized_df["longstanding_illness"] = map_with_check(
        harmonized_df["das_h1"],
        {
            1: "Yes",
            2: "No",
            8: pd.NA,
        },
    )

    # ----------------------------------------------------
    # Illness type (das_h1_1_rec)
    # ----------------------------------------------------

    # categorical → no mapping, NA stays NA
    harmonized_df["illness_type"] = harmonized_df["das_h1_1_rec"]

    # ----------------------------------------------------
    # follow_up_months must already exist (do NOT map)
    # ----------------------------------------------------
    if "follow_up_months" not in harmonized_df.columns:
        raise ValueError("follow_up_months is missing from the loaded dataset.")

    # ----------------------------------------------------
    # Final output (only requested variables)
    # ----------------------------------------------------
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "medication_adherence",
            "suicidal_ideation",
            "suicidal_plan",
            "suicide_attempt",
            "longstanding_illness",
            "illness_type",
        ]
    ]
