import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

# Depression severity = SCL-20 (mean of 20 items, 0-4), already produced as
# ``scl20_mean`` by the loader. Same name as ds_14/15/16/17/18 and ds_27.
#
# WHODAS = physical and social function scales (WHO Disability Assessment
# Schedule subscales + total), already produced as ``whodas_*`` by the loader.
WHODAS_COLS = [
    "whodas_total",
    "whodas_getting_around",
    "whodas_self_care",
    "whodas_household",
]

OUTCOME_COLS = ID_COLS + ["scl20_mean", *WHODAS_COLS]


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Katon 2010 (TEAMcare)."""
    harmonized_df = df.copy()

    for col in WHODAS_COLS:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")

    return harmonized_df[OUTCOME_COLS].copy()
