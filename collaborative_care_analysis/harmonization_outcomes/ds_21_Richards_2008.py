import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.utils import map_with_check

ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Richards 2008.

    Primary outcome: PHQ-9 total (``phq9_total`` in the reshaped frame -- the
    trial's ``DepresSev_Mes`` is "HPQ9"). ``phq9_depressed`` is the PHQ-9 >= 10
    caseness flag.
    """
    harmonized_df = df.copy()

    harmonized_df["phq9_total"] = pd.to_numeric(harmonized_df["phq9_total"], errors="raise")

    harmonized_df["phq9_depressed"] = map_with_check(
        harmonized_df["phq9_depressed"],
        {0: "no", 1: "yes"},
    )

    return harmonized_df[ID_COLS + ["phq9_total", "phq9_depressed"]]
