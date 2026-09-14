import functools

from loguru import logger
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
#
# PHYS_COMORBIDS ("Physical Comorbidities from Chart Abstraction", per the
# codebook) is one row per diagnosed condition, not one row per patient -- 529
# of the 704 patients have at least one row, 175 have none. This loader pivots
# it to one boolean column per condition name plus a total count, broadcast
# onto every visit like the PARTICIPANTS demographics above. A patient absent
# from every pivoted column (all False, count 0) is treated as having no
# recorded comorbidities, not as missing data -- the chart-abstraction form
# was a standard part of the protocol for every randomised patient, not an
# opt-in questionnaire.

_WORKBOOK = RAW_DATASETS_DIR / "25_Rollman_2017" / "OT Meta Data_ Munich.xlsx"

_ID = "studyId"
_LONGITUDINAL_SHEETS = ["PROMIS Depression", "PROMIS Anxiety", "SF-12"]
_BASELINE_SHEETS = ["PHQ-9", "GAD-7"]
_COMORBIDS_SHEET = "PHYS_COMORBIDS"
_COMORBID_COUNT_COL = "phys_comorbid_count"


def load() -> pd.DataFrame:
    book = pd.ExcelFile(_WORKBOOK)

    def prep(sheet: str) -> pd.DataFrame:
        d = book.parse(sheet)
        # blank/whitespace-only cells are missing, before any dtype work
        with pd.option_context("future.no_silent_downcasting", True):
            d = d.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)
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

    participants = prep("PARTICIPANTS")
    missing_id = participants[_ID].isna()
    if missing_id.any():
        logger.warning(f"PARTICIPANTS: dropped {int(missing_id.sum())} rows with no {_ID}.")
        participants = participants.loc[~missing_id]
    duplicated_id = participants[_ID].duplicated(keep=False)
    if duplicated_id.any():
        logger.warning(
            f"PARTICIPANTS: dropped {int(duplicated_id.sum())} rows with a duplicated {_ID}."
        )
        participants = participants.loc[~duplicated_id]
    merged = merged.merge(participants, on=_ID, how="left", validate="many_to_one")

    comorbids = book.parse(_COMORBIDS_SHEET)
    comorbid_flags = comorbids.assign(_present=True).pivot_table(
        index=_ID, columns="phys_comorbid_name", values="_present", aggfunc="any"
    )
    # Reindex to every participant (not just the 529 with >=1 comorbidity row)
    # so absent patients get an explicit False/0 rather than a post-merge NaN.
    # NB: fillna(False) must run BEFORE astype(bool) -- NaN is truthy, so
    # astype(bool) on a column that still has NaN turns every NaN into True.
    comorbid_flags = comorbid_flags.reindex(participants[_ID])
    condition_cols = list(comorbid_flags.columns)
    with pd.option_context("future.no_silent_downcasting", True):
        comorbid_flags[condition_cols] = comorbid_flags[condition_cols].fillna(False).astype(bool)
    comorbid_flags[_COMORBID_COUNT_COL] = (
        comorbids.groupby(_ID).size().reindex(participants[_ID], fill_value=0)
    )
    comorbid_flags = comorbid_flags.reset_index()
    merged = merged.merge(comorbid_flags, on=_ID, how="left")

    merged = merged.rename(columns={_ID: "patient_id"})

    if merged.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    merged = merged.sort_values(["patient_id", "follow_up_months"]).reset_index(drop=True)
    head = ["patient_id", "follow_up_months"]
    return merged[head + [c for c in merged.columns if c not in head]].convert_dtypes()
