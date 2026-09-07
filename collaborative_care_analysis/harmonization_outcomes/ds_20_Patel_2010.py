import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.utils import map_with_check

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Patel 2010 (MANAS).

    - ``CISRTot``    -> ``cisr_total``: Revised Clinical Interview Schedule total
      score (0-48 observed), the continuous symptom-severity measure.
    - ``ICD10case``  -> ``icd10_common_mental_disorder_case``: whether the
      participant met ICD-10 criteria for a common mental disorder. Recovery
      from this at 6 months is the trial's primary outcome.
    """
    harmonized_df = df.copy()

    harmonized_df["cisr_total"] = pd.to_numeric(harmonized_df["CISRTot"], errors="raise")

    harmonized_df["icd10_common_mental_disorder_case"] = map_with_check(
        harmonized_df["ICD10case"],
        {0: "no", 1: "yes"},
    )

    return harmonized_df[ID_COLS + ["cisr_total", "icd10_common_mental_disorder_case"]]
