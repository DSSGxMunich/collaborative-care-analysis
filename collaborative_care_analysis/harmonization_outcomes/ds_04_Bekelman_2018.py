import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

PHQ9_COLS = [f"phq{i:02d}" for i in range(1, 10)]

GAD7_COLS = [f"gad{i:02d}" for i in range(1, 8)]

RENAME_MAP = {
    # PHQ-9
    # "phqtotalv2": "phq9_total_v2", # TODO: Decide whether to include based on Hannah's feedback
    **{f"phq{i:02d}": f"phq9_{i}" for i in range(1, 10)},
    # Additional PHQ functional difficulty question
    "phq10": "phq9_difficulty",
    # GAD-7
    **{f"gad{i:02d}": f"gad7_{i}" for i in range(1, 8)},
    # Additional GAD functional difficulty question
    "gad08": "gad7_difficulty",
    # KCCQ
    "kccqos": "kccq_overall",
    "kccqsf01a": "kccq_sf_1a",
    "kccqsf01b": "kccq_sf_1b",
    "kccqsf01c": "kccq_sf_1c",
    **{f"kccqsf{i:02d}": f"kccq_sf_{i}" for i in range(2, 8)},
    "kccqsf08a": "kccq_sf_8a",
    "kccqsf08b": "kccq_sf_8b",
    "kccqsf08c": "kccq_sf_8c",
    # Pain
    "pegmean": "peg_mean",
    # **{f"peg{i:02d}": f"peg_{i}" for i in range(1, 4)},
    # Fatigue
    "ftgtot": "fatigue_total",
    # **{f"ftg{i:02d}": f"fatigue_{i}" for i in range(1, 9)},
    # Dyspnea
    "dysptot": "dyspnea_total",
    # **{f"dysp{i:02d}": f"dyspnea_{i}" for i in range(1, 4)},
    "dyspmean": "dyspnea_mean",
}

OUTCOME_COLS = ID_COLS + list(RENAME_MAP)


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Bekelman 2018."""

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
