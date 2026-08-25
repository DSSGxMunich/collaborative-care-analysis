import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

PHQ_COLS = [
    "PHQ01",
    "PHQ02",
    "PHQ03",
    "PHQ04",
    "PHQ05",
    "PHQ06",
    "PHQ07",
    "PHQ08",
    "PHQ09",
    "PHQ10",
    "PHQSCORE",
]

KCCQ_COLS = [
    "KCCQCS",
    "KCCQOS",
    "KCCQPL",
    "KCCQQL",
    "KCCQSB",
    "KCCQSE",
    "KCCQSF",
    "KCCQSL",
    "KCCQSS",
    "KCCQTS",
]

GAD7_COLS = [
    "GAD01",
    "GAD02",
    "GAD03",
    "GAD04",
    "GAD05",
    "GAD06",
    "GAD07",
    "GAD08",
    "GADLEVEL",
]

SS_COLS = [
    "SS01",
    "SS02",
    "SS03",
    "SS04",
    "SS05",
    "SS06",
    "SS07",
    "SS08",
    "SS09",
    "SS10",
    "SSSCORE",
]

OUTCOME_COLS = ID_COLS + PHQ_COLS + KCCQ_COLS + GAD7_COLS + SS_COLS

RENAME_MAP = {
    # PHQ
    **{f"PHQ{i:02d}": f"phq{i:02d}" for i in range(1, 11)},
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
    **{f"GAD{i:02d}": f"gad{i:02d}" for i in range(1, 9)},
    "GADLEVEL": "gad7_total",
    # Signs and symptoms
    **{f"SS{i:02d}": f"ss{i:02d}" for i in range(1, 11)},
    "SSSCORE": "ss_total",
}


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Bekelman 2015."""

    harmonized_df = df[OUTCOME_COLS].copy()

    harmonized_df.rename(
        columns=RENAME_MAP,
        inplace=True,
    )

    return harmonized_df
