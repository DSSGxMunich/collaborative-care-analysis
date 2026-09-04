import functools

import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Rollman 2017 = the "OT" (Online Treatment) trial: "Effectiveness of Online
# Collaborative Care for Treating Mood and Anxiety Disorders in Primary Care"
# (JAMA Psychiatry 2018). 3-arm RCT, N = 704: guided online computerised CBT
# alone (CCBT alone, n = 301), CCBT + a moderated internet support group
# (CCBT+ISG, n = 302), or usual care (n = 101). Primary outcome: mental HRQoL
# measured with PROMIS at 6 months, with durability assessed at 12 months.
#
# The workbook ships one sheet per instrument. PROMIS Depression / PROMIS
# Anxiety / SF-12 are longitudinal (months 0/3/6/12); PHQ-9 and GAD-7 are
# baseline only. This loader joins them into one row per patient-visit and
# broadcasts the PARTICIPANTS demographics onto every visit.

_WORKBOOK = RAW_DATASETS_DIR / "25_Rollman_2017" / "OT Meta Data_ Munich.xlsx"

_ID = "studyId"
_LONGITUDINAL_SHEETS = ["PROMIS Depression", "PROMIS Anxiety", "SF-12"]
_BASELINE_SHEETS = ["PHQ-9", "GAD-7"]


def load() -> pd.DataFrame:
    book = pd.ExcelFile(_WORKBOOK)

    def prep(sheet: str) -> pd.DataFrame:
        d = book.parse(sheet)
        return d.drop(columns=[c for c in ("tpid",) if c in d.columns])

    longitudinal = [
        prep(s).rename(columns={"month": "follow_up_months"}) for s in _LONGITUDINAL_SHEETS
    ]
    merged = functools.reduce(
        lambda left, right: left.merge(right, on=[_ID, "follow_up_months"], how="outer"),
        longitudinal,
    )

    for sheet in _BASELINE_SHEETS:
        baseline = prep(sheet)
        baseline["follow_up_months"] = baseline.pop("month") if "month" in baseline.columns else 0
        merged = merged.merge(baseline, on=[_ID, "follow_up_months"], how="left")

    participants = book.parse("PARTICIPANTS")
    if participants[_ID].duplicated().any():
        raise ValueError("PARTICIPANTS sheet is not unique on studyId")
    merged = merged.merge(participants, on=_ID, how="left", validate="many_to_one")

    merged = merged.rename(columns={_ID: "patient_id"})

    if merged.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    merged = merged.sort_values(["patient_id", "follow_up_months"]).reset_index(drop=True)
    head = ["patient_id", "follow_up_months"]
    return merged[head + [c for c in merged.columns if c not in head]].convert_dtypes()
