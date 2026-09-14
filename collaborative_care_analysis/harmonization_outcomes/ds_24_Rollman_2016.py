import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]

RENAME_MAP = {
    "phq9_total": "phq9_total",  # PHQ-9 depression total
    "sigha_total": "sigha_total",  # SIGH-A anxiety total -- co-primary outcome
    # SF-36v2 norm-based component summaries (US general population: mean 50,
    # SD 10). MCS is the trial's other co-primary outcome. Norm-based scoring
    # can place a severely impaired respondent slightly below zero, so these are
    # not bounded at 0 the way a raw scale score would be.
    "mcs": "sf36_mental_component_summary",
    "pcs": "sf36_physical_component_summary",
}


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Rollman 2016 (RELAX).

    Co-primary outcomes: mental HRQoL (SF-36 MCS) and anxiety (SIGH-A) over
    24 months.
    """
    harmonized_df = df.copy()
    for col in RENAME_MAP:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")
    return harmonized_df[ID_COLS + list(RENAME_MAP)].rename(columns=RENAME_MAP, errors="raise")
