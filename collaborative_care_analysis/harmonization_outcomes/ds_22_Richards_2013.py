import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]

RENAME_MAP = {
    "phq9_total": "phq9_total",  # Depres_* -- PHQ-9 total, primary outcome
    "phq9_q9": "phq9_9",  # suicidal-ideation item
    "eq5d_total": "eq5d_total",  # stored total, not computed from items
    # gad7_total: stored total is NOT on the true 0-21 GAD-7 range for a
    # subset of rows (max 26 at baseline; see git history for the full
    # derivation). Caller is responsible for excluding/flagging rows > 21
    # before treating this as a standard GAD-7 score.
    "gad7_total": "gad7_total",
}

# SF-36 items grouped into the 8 standard RAND-36/SF-36 subscales.
# Note: sf36_q2 ("health change vs. last year") is not part of any subscale
# in standard SF-36 scoring and is intentionally excluded from all groups.
SF36_SUBSCALE_ITEMS = {
    "sf36_physical_functioning_value": [
        "sf36_q3a",
        "sf36_q3b",
        "sf36_q3c",
        "sf36_q3d",
        "sf36_q3e",
        "sf36_q3f",
        "sf36_q3g",
        "sf36_q3h",
        "sf36_q3i",
        "sf36_q3j",
    ],
    "sf36_role_physical_value": [
        "sf36_q4a",
        "sf36_q4b",
        "sf36_q4c",
        "sf36_q4d",
    ],
    "sf36_bodily_pain_value": [
        "sf36_q7",
        "sf36_q8",
    ],
    "sf36_general_health_value": [
        "sf36_q1",
        "sf36_q11a",
        "sf36_q11b",
        "sf36_q11c",
        "sf36_q11d",
    ],
    "sf36_vitality_value": [
        "sf36_q9a",
        "sf36_q9e",
        "sf36_q9g",
        "sf36_q9i",
    ],
    "sf36_social_functioning_value": [
        "sf36_q6",
        "sf36_q10",
    ],
    "sf36_role_emotional_value": [
        "sf36_q5a",
        "sf36_q5b",
        "sf36_q5c",
    ],
    "sf36_mental_health_value": [
        "sf36_q9b",
        "sf36_q9c",
        "sf36_q9d",
        "sf36_q9f",
        "sf36_q9h",
    ],
}

SF36_ITEM_COLS = sorted({c for cols in SF36_SUBSCALE_ITEMS.values() for c in cols})

SF36_MISSING_CODE = 999


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Richards 2013 (CADET)."""
    harmonized_df = df.copy()

    for col in RENAME_MAP:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")

    for col in SF36_ITEM_COLS:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")
        harmonized_df[col] = harmonized_df[col].mask(
            harmonized_df[col] == SF36_MISSING_CODE, pd.NA
        )

    for subscale_col, item_cols in SF36_SUBSCALE_ITEMS.items():
        harmonized_df[subscale_col] = harmonized_df[item_cols].sum(axis=1, skipna=True)

    # Select the pre-rename columns first, then rename.
    output_cols = ID_COLS + list(RENAME_MAP) + list(SF36_SUBSCALE_ITEMS)
    return harmonized_df[output_cols].rename(columns=RENAME_MAP)
