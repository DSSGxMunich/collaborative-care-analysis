import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR / "04_Bekelman_2018" / "CASAforIPD-MA (1).csv",
):
    df = pd.read_csv(file_path)

    # 1. Remove caregiver rows:
    # any non-missing value in a cg_* column identifies a caregiver row.
    cg_cols = [col for col in df.columns if col.startswith("cg_")]
    is_caregiver = df[cg_cols].notna().any(axis=1)
    df = df.loc[~is_caregiver].copy()

    # 2. Keep rows with at least one relevant patient score available.
    patient_score_cols = [
        "phqtotal",
        "phqtotalv2",
        "gadtotal",
        "ticstot",
        "ticstotv2",
        "kccqos",
    ]

    has_patient_score = df[patient_score_cols].notna().any(axis=1)
    df = df.loc[has_patient_score].copy()

    return df
