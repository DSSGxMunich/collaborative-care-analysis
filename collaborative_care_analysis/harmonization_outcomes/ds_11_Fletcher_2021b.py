import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

PHQ9_COLS = [
    "phq2wk_noint",
    "phq2wk_down",
    "phq2wk_sleep",
    "phq2wk_energy",
    "phq2wk_eat",
    "phq2wk_bad",
    "phq2wk_conc",
    "phq2wk_speed",
    "phq2wk_dead",
]

BASELINE_PHQ9_COLS = [f"{col}_t" for col in PHQ9_COLS]

GAD7_COLS = [f"gad{i}" for i in range(1, 8)]

RENAME_MAP = {
    # PHQ-9 items
    "phq2wk_noint": "phq9_1",
    "phq2wk_down": "phq9_2",
    "phq2wk_sleep": "phq9_3",
    "phq2wk_energy": "phq9_4",
    "phq2wk_eat": "phq9_5",
    "phq2wk_bad": "phq9_6",
    "phq2wk_conc": "phq9_7",
    "phq2wk_speed": "phq9_8",
    "phq2wk_dead": "phq9_9",
    # GAD-7 items
    **{f"gad{i}": f"gad7_{i}" for i in range(1, 8)},
    # AQoL-8D items
    **{f"aqol{i}": f"aqol8d_{i}" for i in range(1, 36)},
    # AQoL-8D dimensions
    "vIL": "aqol8d_independent_living",
    "vHap": "aqol8d_happiness",
    "vMH": "aqol8d_mental_health",
    "vCop": "aqol8d_coping",
    "vRel": "aqol8d_relationships",
    "vSW": "aqol8d_self_worth",
    "vPa": "aqol8d_pain",
    "vS": "aqol8d_senses",
    "AQoL8DUtility": "aqol8d_utility",
    # Mental Health Self-Efficacy Scale
    **{f"mhses{i}": f"mhses_{i}" for i in range(1, 7)},
}

OUTCOME_COLS = ID_COLS + list(RENAME_MAP) + BASELINE_PHQ9_COLS


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Fletcher 2021b."""

    harmonized_df = df[OUTCOME_COLS].copy()

    # Use the baseline PHQ-9 item variables for the month-0 row.
    is_baseline = harmonized_df["follow_up_months"].eq(0)

    for phq_col, baseline_col in zip(
        PHQ9_COLS,
        BASELINE_PHQ9_COLS,
        strict=True,
    ):
        harmonized_df.loc[is_baseline, phq_col] = harmonized_df.loc[
            is_baseline,
            baseline_col,
        ]

    # Calculate PHQ-9 total only when all nine items are available.
    harmonized_df["phq9_total"] = (
        harmonized_df[PHQ9_COLS]
        .apply(pd.to_numeric, errors="raise")
        .sum(
            axis=1,
            min_count=len(PHQ9_COLS),
        )
        .astype("Int64")
    )

    # Calculate GAD-7 total from item-level scores.
    harmonized_df["gad7_total"] = (
        harmonized_df[GAD7_COLS]
        .apply(pd.to_numeric, errors="raise")
        .sum(
            axis=1,
            min_count=len(GAD7_COLS),
        )
        .astype("Int64")
    )

    # Drop baseline PHQ source columns after creating the long-format items.
    harmonized_df.drop(
        columns=BASELINE_PHQ9_COLS,
        inplace=True,
    )

    return harmonized_df.rename(
        columns=RENAME_MAP,
        errors="raise",
    )
