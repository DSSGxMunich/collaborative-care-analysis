import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Rollman 2009 (Bypassing the Blues).

    Depression severity = HRSD-17 (Hamilton Rating Scale for Depression, 17
    item), a co-primary outcome. ``hrsd17_suicide_item`` is HRSD item 3.
    """
    harmonized_df = df.copy()
    for col in ["hrsd17_total", "hrsd17_suicide_item"]:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")
    return harmonized_df[ID_COLS + ["hrsd17_total", "hrsd17_suicide_item"]]
