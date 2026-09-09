import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Davidson 2013 (CODIACS).

    Primary outcome: Beck Depression Inventory (the original BDI-I, per the
    paper). Assessed at baseline (``bdiscore_01`` -- the enrolment screening
    BDI, present for all 150 patients) and at 2/4/6 months (``bdiscore``,
    produced by the wide->long reshape in ``load()``).
    """
    harmonized_df = df.copy()

    bdi = pd.to_numeric(harmonized_df["bdiscore"], errors="raise")
    is_baseline = harmonized_df["follow_up_months"].eq(0)
    bdi = bdi.mask(is_baseline, pd.to_numeric(harmonized_df["bdiscore_01"], errors="raise"))

    harmonized_df["bdi1_total"] = bdi

    return harmonized_df[ID_COLS + ["bdi1_total"]]
