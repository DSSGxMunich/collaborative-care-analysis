import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]

RENAME_MAP = {
    "promis_depression_total": "promis_depression_total",  # raw sum of 8 items
    "promis_depression_conversion": "promis_depression_tscore",  # T-score
    "phq9_total": "phq9_total",  # baseline only
    # SF-12 norm-based component summaries (US general population: mean 50,
    # SD 10). MCS is the trial's actual primary outcome -- the paper's Methods
    # section lists it first and powers the trial on it; PROMIS Depression is a
    # secondary "symptom" measure. Same construct/naming as ds_24's SF-36 MCS/PCS.
    "MCS": "sf12_mental_component_summary",
    "PCS": "sf12_physical_component_summary",
}


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Rollman 2017 (OT trial).

    Primary outcome: mental HRQoL (SF-12 MCS) at 6 months, with PROMIS
    Depression/Anxiety and PHQ-9 as secondary symptom measures.
    """
    harmonized_df = df.copy()
    for col in RENAME_MAP:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")
    return harmonized_df[ID_COLS + list(RENAME_MAP)].rename(columns=RENAME_MAP)
