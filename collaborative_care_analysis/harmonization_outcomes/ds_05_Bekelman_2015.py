import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

RENAME_MAP = {
    # PHQ-9
    **{f"PHQ{i:02d}": f"phq9_{i}" for i in range(1, 10)},
    "PHQ10": "phq9_difficulty",
    "PHQSCORE": "phq9_total",
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
    "GADLEVEL": "gad7_total",
    # Signs and symptoms
    # **{f"SS{i:02d}": f"ss_{i}" for i in range(1, 11)},
    "SSSCORE": "ss_total",
}

OUTCOME_COLS = ID_COLS + list(RENAME_MAP)


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Bekelman 2015."""

    harmonized_df = df[OUTCOME_COLS].copy()

    return harmonized_df.rename(
        columns=RENAME_MAP,
        errors="raise",
    )
