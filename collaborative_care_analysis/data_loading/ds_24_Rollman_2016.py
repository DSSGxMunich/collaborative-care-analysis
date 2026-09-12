import functools
import re

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Rollman 2016 = the "RELAX" trial: "Telephone-Delivered Stepped Collaborative
# Care for Treating Anxiety in Primary Care" (J Gen Intern Med 2017;32:245-55).
# N = 329. Highly anxious primary-care patients randomised to telephone-delivered
# stepped collaborative care (CC) vs usual care (UC); a moderately-anxious
# watchful-waiting (WW) cohort was randomised later if symptoms worsened.
# Primary outcomes: mental HRQoL (SF-36 MCS) and anxiety (SIGH-A) over 24 months.
#
# Every sheet in the workbook is loaded except SelectNotes, and each is
# classified by its own shape rather than by a hardcoded list. There are three:
#
#   * per-visit -- carries a ``month`` column (PHQ-9, SIGH-A, GADSS, PDSS,
#     SF-36v2). Keyed by ``acrid`` + month, outer-joined into one row per
#     patient-visit. Must be unique on that key.
#   * per-patient -- no ``month`` column, one row per ``acrid`` (PARTICIPANTS).
#     Broadcast across every visit row of that patient.
#   * repeating detail -- no ``month`` column and several rows per ``acrid``
#     (PHYS_COMORBIDS: one row per patient *per comorbidity*, with name, ICD-9,
#     onset and medication). This does not fit a patient-visit grain, so it is
#     first collapsed to one row per patient (see _collapse_repeating) and then
#     broadcast like any other per-patient sheet.
#
# Classifying by shape means a sheet that changes grain in a re-export is merged
# correctly instead of silently losing rows, and a newly added sheet is picked
# up rather than dropped.
#
# PARTICIPANTS IS THE ROSTER OF ENROLLED PATIENTS AND IS JOINED INNER.
# The instrument sheets reach further than the trial: SIGHA has 374 distinct
# ``acrid``, GADSS 372, PDSS 373, SF36v2 335, PHQ9 331, against 329 in
# PARTICIPANTS -- which is the published N. The extra ids carry a single
# baseline row each and appear in no other sheet, i.e. screened-but-not-enrolled
# patients. A left join kept them with a null arm and null demographics, which
# is worse than not having them: they were silently counted as patients and
# ``map_with_check`` cannot flag a null ``group``. The inner join plus the
# check below pins the cohort to the enrolled sample. Every *other*
# per-patient sheet is joined left onto that cohort, so it can contribute
# columns but can never add or drop a patient.
#
# "Enrolled", not "randomised": the 329 are 250 highly anxious patients
# randomised at baseline (126 UC / 124 CC) plus 79 watchful-waiting patients,
# of whom only 23 were later randomised. The other 56 were never randomised and
# are kept here with their own ``group`` value; harmonization_treatment maps
# "WW never randomized" to a null arm.
_ENROLLED_PATIENT_COUNT = 329
_ID = "acrid"
_MONTHS = "follow_up_months"

# The roster sheet that defines the cohort (see the note above).
_COHORT_SHEET = "PARTICIPANTS"

# Sheets that are not data. Compared case- and whitespace-insensitively.
_EXCLUDED_SHEETS: set[str] = {"selectnotes"}

# Guard against a re-export quietly adding or dropping a sheet: PHQ9, SIGHA,
# GADSS, PDSS, SF36v2, PHYS_COMORBIDS and PARTICIPANTS.
_EXPECTED_SHEET_COUNT = 7

# Raw column names that carry the visit index, and columns dropped everywhere.
_MONTH_ALIASES = ("month", _MONTHS)
_DROP_COLUMNS = ("timept",)

# Separator used when a repeating sheet's detail columns are folded into one
# row per patient.
_LIST_JOIN = "; "


def _normalise(sheet: str) -> str:
    return sheet.strip().casefold()


def _column_stem(sheet: str) -> str:
    """A sheet name usable as a column prefix: PHYS_COMORBIDS -> phys_comorbids."""
    return re.sub(r"\W+", "_", sheet.strip()).strip("_").casefold()


def _prep(book: pd.ExcelFile, sheet: str) -> pd.DataFrame:
    """Parse one sheet and normalise its key columns."""
    frame = book.parse(sheet).drop(columns=list(_DROP_COLUMNS), errors="ignore")
    # treat blank or whitespace-only cells as missing, before any dtype work
    with pd.option_context("future.no_silent_downcasting", True):
        frame = frame.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)

    if _ID not in frame.columns:
        raise ValueError(
            f"Sheet {sheet!r} has no {_ID!r} column and cannot be joined; "
            f"add it to _EXCLUDED_SHEETS if it is not patient data."
        )

    aliases = [alias for alias in _MONTH_ALIASES if alias in frame.columns]
    if len(aliases) > 1:
        raise ValueError(
            f"Sheet {sheet!r} carries more than one visit column ({aliases}); "
            f"cannot tell which indexes the follow-up."
        )
    if aliases:
        frame = frame.rename(columns={aliases[0]: _MONTHS})

    missing_id = frame[_ID].isna()
    if missing_id.any():
        logger.warning(f"Sheet {sheet!r}: dropped {int(missing_id.sum())} rows with no {_ID}.")
        frame = frame.loc[~missing_id]

    return frame


def _join_distinct(values: pd.Series) -> str | float:
    """Distinct non-null values in order of appearance, joined into one string."""
    text = values.dropna().astype(str).str.strip()
    text = text[text != ""]
    if text.empty:
        return pd.NA
    return _LIST_JOIN.join(dict.fromkeys(text))


def _collapse_repeating(sheet: str, frame: pd.DataFrame) -> pd.DataFrame:
    """Fold a one-row-per-(patient, item) sheet down to one row per patient.

    PHYS_COMORBIDS holds one row per comorbidity per patient, so it cannot be
    broadcast across visits as-is. Each patient gets a row count (the useful
    numeric feature, e.g. ``n_phys_comorbids``) plus every detail column folded
    into a delimiter-joined string, which keeps the underlying values readable
    without inventing clinical categories. Turning the names into one-hot
    indicators is a modelling decision and belongs downstream, not here.

    Patients absent from the sheet are left as <NA> rather than 0 by the join in
    ``load``: absence may mean "none recorded" or "not assessed", and the loader
    should not decide which.
    """
    detail_cols = [col for col in frame.columns if col != _ID]
    grouped = frame.groupby(_ID, dropna=False)

    collapsed = pd.DataFrame({f"n_{_column_stem(sheet)}": grouped.size()})
    for col in detail_cols:
        collapsed[col] = grouped[col].agg(_join_distinct)

    logger.warning(
        f"Sheet {sheet!r} repeats on {_ID} ({len(frame)} rows over "
        f"{frame[_ID].nunique()} patients); collapsed to one row per patient as "
        f"'n_{_column_stem(sheet)}' plus {len(detail_cols)} detail column(s) "
        f"joined with {_LIST_JOIN!r}."
    )
    return collapsed.reset_index()


def _assert_no_shared_columns(sheets: dict[str, pd.DataFrame]) -> None:
    """Raise if two sheets contribute the same non-key column."""
    seen: dict[str, str] = {}
    for name, frame in sheets.items():
        for col in frame.columns:
            if col in (_ID, _MONTHS):
                continue
            if col in seen:
                raise ValueError(
                    f"Column {col!r} appears in both {seen[col]!r} and {name!r}; "
                    f"merging them would produce _x / _y columns."
                )
            seen[col] = name


def load(
    file_path=RAW_DATASETS_DIR / "24_Rollman_2016" / "RELAX Meta Data_ Munich.xlsx",
) -> pd.DataFrame:
    book = pd.ExcelFile(file_path)

    sheet_names = [
        sheet for sheet in book.sheet_names if _normalise(sheet) not in _EXCLUDED_SHEETS
    ]
    if len(sheet_names) != _EXPECTED_SHEET_COUNT:
        raise ValueError(
            f"Expected {_EXPECTED_SHEET_COUNT} data sheets, found "
            f"{len(sheet_names)}: {sheet_names}. Update _EXPECTED_SHEET_COUNT or "
            f"_EXCLUDED_SHEETS if the workbook legitimately changed."
        )
    if _COHORT_SHEET not in sheet_names:
        raise ValueError(f"Cohort sheet {_COHORT_SHEET!r} not in workbook: {sheet_names}")

    sheets = {name: _prep(book, name) for name in sheet_names}

    cohort = sheets.pop(_COHORT_SHEET)
    if _MONTHS in cohort.columns:
        raise ValueError(
            f"{_COHORT_SHEET!r} unexpectedly carries a visit column; it is joined "
            f"on {_ID} alone to define the cohort."
        )
    if cohort[_ID].duplicated().any():
        raise ValueError(
            f"{_COHORT_SHEET!r} defines the cohort and must be unique on {_ID} "
            f"({int(cohort[_ID].duplicated().sum())} duplicate ids)."
        )

    per_visit = {n: f for n, f in sheets.items() if _MONTHS in f.columns}
    if not per_visit:
        raise ValueError(
            f"No sheet carries a visit column, so there is nothing to stack; "
            f"looked for {_MONTH_ALIASES} in {sorted(sheets)}."
        )

    # A per-visit sheet that repeats within (patient, visit) is a data-integrity
    # question rather than a list structure, so it is refused instead of being
    # quietly collapsed the way a repeating patient-level sheet is.
    for name, frame in per_visit.items():
        if frame.duplicated([_ID, _MONTHS]).any():
            n_dup = int(frame.duplicated([_ID, _MONTHS]).sum())
            raise ValueError(
                f"Sheet {name!r} has {n_dup} duplicate ({_ID}, {_MONTHS}) rows; "
                f"a per-visit sheet must be unique on that key."
            )

    # Per-patient sheets: unique on acrid are broadcast as they are, repeating
    # detail tables (PHYS_COMORBIDS) are collapsed to one row per patient first.
    per_patient: dict[str, pd.DataFrame] = {}
    for name, frame in sheets.items():
        if _MONTHS in frame.columns:
            continue
        per_patient[name] = (
            _collapse_repeating(name, frame) if frame[_ID].duplicated().any() else frame
        )

    logger.info(
        f"Per-visit sheets: {sorted(per_visit)}; "
        f"per-patient sheets: {sorted([*per_patient, _COHORT_SHEET])}"
    )

    # The sheets should share only the join keys; anything else in common would
    # be resolved into silent _x / _y columns by the merges below. Checked after
    # collapsing so the generated count columns are covered too.
    _assert_no_shared_columns({**per_visit, **per_patient, _COHORT_SHEET: cohort})

    merged = functools.reduce(
        lambda left, right: left.merge(right, on=[_ID, _MONTHS], how="outer"),
        per_visit.values(),
    )

    # Inner: drops the screened-but-not-enrolled ids (see the note above).
    merged = merged.merge(cohort, on=_ID, how="inner", validate="many_to_one")

    n_patients = merged[_ID].nunique()
    if n_patients != _ENROLLED_PATIENT_COUNT:
        raise ValueError(
            f"Expected {_ENROLLED_PATIENT_COUNT} enrolled patients "
            f"(the published RELAX N), got {n_patients}."
        )

    # Left: the remaining per-patient sheets contribute columns to the cohort
    # but must not be able to add or drop a patient.
    for name, frame in per_patient.items():
        covered = int(merged[_ID].drop_duplicates().isin(frame[_ID]).sum())
        if covered < _ENROLLED_PATIENT_COUNT:
            logger.warning(
                f"Sheet {name!r} covers {covered}/{_ENROLLED_PATIENT_COUNT} "
                f"enrolled patients; the rest get <NA> for its columns."
            )
        merged = merged.merge(frame, on=_ID, how="left", validate="many_to_one")

    merged = merged.rename(columns={_ID: "patient_id"})

    if merged.duplicated(["patient_id", _MONTHS]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    merged = merged.sort_values(["patient_id", _MONTHS]).reset_index(drop=True)
    head = ["patient_id", _MONTHS]
    return merged[head + [c for c in merged.columns if c not in head]].convert_dtypes()
