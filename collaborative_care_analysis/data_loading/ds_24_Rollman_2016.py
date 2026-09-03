import functools

import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Rollman 2016 = the "RELAX" trial: "Telephone-Delivered Stepped Collaborative
# Care for Treating Anxiety in Primary Care" (J Gen Intern Med 2017;32:245-55).
# N = 329. Highly anxious primary-care patients randomised to telephone-delivered
# stepped collaborative care (CC) vs usual care (UC); a moderately-anxious
# watchful-waiting (WW) cohort was randomised later if symptoms worsened.
# Primary outcomes: mental HRQoL (SF-36 MCS) and anxiety (SIGH-A) over 24 months.
#
# The workbook has one long sheet per instrument (PHQ-9, SIGH-A, GADSS, PDSS,
# SF-36v2), each keyed by ``acrid`` and ``month`` (0/2/4/8/12/18/24). This loader
# outer-joins them into one row per patient-visit and attaches the PARTICIPANTS
# demographics. SF36v2 carries the trial's co-primary outcome (SF-36 MCS), so it
# is loaded alongside the symptom instruments.
#
# PARTICIPANTS IS THE ROSTER OF RANDOMISED PATIENTS AND IS JOINED INNER.
# The instrument sheets reach further than the trial: SIGHA has 374 distinct
# ``acrid``, GADSS 372, PDSS 373, SF36v2 335, PHQ9 331, against 329 in
# PARTICIPANTS -- which is the published N. The extra ids carry a single
# baseline row each and appear in no other sheet, i.e. screened-but-not-enrolled
# patients. A left join kept them with a null arm and null demographics, which
# is worse than not having them: they were silently counted as patients and
# ``map_with_check`` cannot flag a null ``group``. The inner join plus the
# assertion below pins the cohort to the randomised sample.
_RANDOMISED_PATIENT_COUNT = 329

_WORKBOOK = RAW_DATASETS_DIR / "24_Rollman_2016" / "RELAX Meta Data_ Munich.xlsx"

_ID = "acrid"
_INSTRUMENT_SHEETS = ["PHQ9", "SIGHA", "GADSS", "PDSS", "SF36v2"]


def _assert_no_shared_columns(sheets: dict[str, pd.DataFrame]) -> None:
    """Raise if two instrument sheets contribute the same non-key column."""
    seen: dict[str, str] = {}
    for name, frame in sheets.items():
        for col in frame.columns:
            if col in (_ID, "follow_up_months"):
                continue
            if col in seen:
                raise ValueError(
                    f"Column {col!r} appears in both {seen[col]!r} and {name!r}; "
                    f"merging them would produce _x / _y columns."
                )
            seen[col] = name


def load() -> pd.DataFrame:
    book = pd.ExcelFile(_WORKBOOK)

    def prep(sheet: str) -> pd.DataFrame:
        d = book.parse(sheet).drop(columns=["timept"], errors="ignore")
        return d.rename(columns={"month": "follow_up_months"})

    instruments = [prep(sheet) for sheet in _INSTRUMENT_SHEETS]

    # The sheets share only the join keys; anything else in common would be
    # resolved into silent _x / _y columns by the merge below.
    _assert_no_shared_columns(dict(zip(_INSTRUMENT_SHEETS, instruments)))

    merged = functools.reduce(
        lambda left, right: left.merge(right, on=[_ID, "follow_up_months"], how="outer"),
        instruments,
    )

    participants = book.parse("PARTICIPANTS")
    if participants[_ID].duplicated().any():
        raise ValueError("PARTICIPANTS sheet is not unique on acrid")
    merged = merged.merge(participants, on=_ID, how="inner", validate="many_to_one")

    n_patients = merged[_ID].nunique()
    if n_patients != _RANDOMISED_PATIENT_COUNT:
        raise ValueError(
            f"Expected {_RANDOMISED_PATIENT_COUNT} randomised patients "
            f"(the published RELAX N), got {n_patients}."
        )

    merged = merged.rename(columns={_ID: "patient_id"})

    if merged.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    merged = merged.sort_values(["patient_id", "follow_up_months"]).reset_index(drop=True)
    head = ["patient_id", "follow_up_months"]
    return merged[head + [c for c in merged.columns if c not in head]].convert_dtypes()
