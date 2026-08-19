import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Bekelman 2018."""

    harmonized_df = df[
        [
            COLNAME_STUDYID,
            "studyid", # identifier for patient and caregiver
            "timept",  # 0-screening, 1-baseline, 2-3month, 3-6month, 4-12month
            "kccqos",  # overall KCCQ score, heart-failure-specific quality of life
            "phqtotal",  # depressive symptom (PHQ-9)
            "phqtotalv2",  # alt version of PHQ9; 21 less values than phqtotal where at least one PHQ item is missing,
            # and 3 rows with a completely different score from phqtotal
            "gadtotal",  # anxiety symptom
            # "ticstot", # telephone Interview for Cognitive Status (TICS) used for screening
            # "ticstotv2", # telephone Interview for Cognitive Status (TICS) used for screening
            "pegmean",  # pain
            "ftgtot",  # Fatigue total
            "dysptot",  # Dyspnea total
            "dyspmean",  # Dyspnea mean
        ]
    ].copy()

    return harmonized_df
