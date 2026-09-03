import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]

RENAME_MAP = {
    "phq9_total": "phq9_total",  # Depres_* -- PHQ-9 total, primary outcome
    "phq9_q9": "phq9_9",  # suicidal-ideation item
}

# GAD-7 IS DELIBERATELY NOT HARMONIZED HERE.
#
# ``Baseline_GAD7_Total`` and its follow-up counterparts are labelled
# "Generalised Anxiety Disorder Total score", but they do not lie on the GAD-7's
# 0-21 range:
#
#   wave        n     min   max   n > 21
#   baseline   579     1     26     100
#   4 months   496     0     25      48
#   12 months  479     0     25      42
#   36 months  268     0     25      21
#
# The cause is visible in "Richards 2013_36m CLEANEDn.sav", the only file that
# ships the underlying items: CADET collected **eight** GAD questions, Q1-Q7
# (0-3, the GAD-7 proper) plus a Q8 impairment item scored 0-4 -- the analogue
# of PHQ9_Q10, which is not part of a GAD-7 score. Summing Q1-Q7 there gives a
# clean 0-21 scale (max exactly 21, mean 8.1), whereas the stored total reaches
# 25.
#
# The stored total is not simply "Q1-Q8" either: it equals sum(Q1..Q8) for only
# 46% of rows and sum(Q1..Q7) for 4%, so it cannot be corrected by subtracting
# Q8. And the item columns exist only in the 36-month file -- the CLEANED file
# this loader reads carries just the totals -- so a correct 0-21 score cannot be
# recomputed for baseline / 4 / 12 months at all.
#
# Emitting it as ``gad7_total`` would put a contaminated, non-reproducible scale
# in the same column as the genuine 0-21 totals from ds_04/05/08/10/11/26/30.
# Restore this once the scoring is confirmed with the study team; the raw values
# stay available in the exported dataset under the loader's ``gad7_total``.


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Richards 2013 (CADET)."""
    harmonized_df = df.copy()
    for col in RENAME_MAP:
        harmonized_df[col] = pd.to_numeric(harmonized_df[col], errors="raise")
    return harmonized_df[ID_COLS + list(RENAME_MAP)].rename(columns=RENAME_MAP)
