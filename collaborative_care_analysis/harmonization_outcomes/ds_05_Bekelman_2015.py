import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

PHQ9_COLS = [f"PHQ{i:02d}" for i in range(1, 10)]

GAD7_COLS = [f"GAD{i:02d}" for i in range(1, 8)]

RENAME_MAP = {
    # PHQ-9
    **{f"PHQ{i:02d}": f"phq9_{i}" for i in range(1, 10)},
    "PHQ10": "phq9_difficulty",
    # KCCQ
    "KCCQCS": "kccq_cs",
    "KCCQOS": "kccq_os",
    "KCCQPL": "kccq_pl",
    "KCCQQL": "kccq_ql",
    "KCCQSB": "kccq_sb",
    "KCCQSE": "kccq_se",
    "KCCQSF": "kccq_sf",
    "KCCQSL": "kccq_sl",
    "KCCQSS": "kccq_ss",
    "KCCQTS": "kccq_ts",
    # GAD-7
    **{f"GAD{i:02d}": f"gad7_{i}" for i in range(1, 8)},
    # Signs and symptoms
    # **{f"SS{i:02d}": f"ss_{i}" for i in range(1, 11)},
    "SSSCORE": "ss_total",
}

OUTCOME_COLS = ID_COLS + list(RENAME_MAP)


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Bekelman 2015."""

    harmonized_df = df[OUTCOME_COLS].copy()

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

    # Calculate GAD-7 total only when all seven items are available.
    harmonized_df["gad7_total"] = (
        harmonized_df[GAD7_COLS]
        .apply(pd.to_numeric, errors="raise")
        .sum(
            axis=1,
            min_count=len(GAD7_COLS),
        )
        .astype("Int64")
    )

    return harmonized_df.rename(
        columns=RENAME_MAP,
        errors="raise",
    )
