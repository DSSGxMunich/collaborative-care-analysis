import re

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import ensure_unzipped

# Wells 2000 = the "Partners in Care" (PIC) trial (JAMA 2000;283:212-220):
# "Impact of disseminating quality improvement programs for depression in
# managed primary care." 46 primary-care clinics in 6 US managed-care
# organisations, cluster-randomised to usual care vs one of two
# quality-improvement (QI) programmes -- QI-Meds (nurse-supported medication
# management) or QI-Therapy (access to trained CBT psychotherapists). N = 1356.
# Depression measured with the CES-D; follow-ups at 6, 12, 24 months and
# long-term (48, 96 months).
#
# The raw archive is a merged SPSS file, wide, with each repeated measure
# suffixed by its month (00/06/12/18/24/48/96). This loader stacks those into
# long format. ``INTERV`` is the two-level arm (1 = QI, n=913; 0 = control,
# n=443) and ``CLNTYPE`` the three-level one (T = QI-Therapy 489, M = QI-Meds
# 424, U = usual care 443); both match the paper exactly. The zip this used to
# be extracted from is no longer in the study folder, which now ships the
# extracted files.
#
# Two groups of columns do not follow that rule and are mapped
# explicitly below: the P<month>CES.. CES-D items, and a handful of variables
# whose names predate the suffix convention (_IRREGULAR_TIME_VARYING).
#
# DEPRESSION MEASURES -- three different CES-D scorings live in this file and
# they are NOT interchangeable:
#   CESD<mm>    "Sum across 23 depressed symptoms 0-100 scale"  -> stem CESD
#   NWCESD<mm>  "NEW CESD SCALE", the 23-item sum, observed 0-67,
#               dichotomised at >= 20 (DPCESD<mm>)              -> stem NWCESD
#   CESD1820    "CESD 20 ITEMS MAX=60", the standard 20-item
#               CES-D, month 18 only                            -> stem CESD20
# harmonization_outcomes keeps the 23-item and 20-item scales under separate
# names for this reason.

_STUDY_DIR = RAW_DATASETS_DIR / "32_Wells_2000"
_MARKER = _STUDY_DIR / "Wells Trial" / "Wells 2000 full merged dataset.sav"

ID_COL = "AID"

TIMEPOINT_SUFFIXES = ["00", "06", "12", "18", "24", "48", "96"]
SUFFIX_TO_MONTHS = {s: int(s) for s in TIMEPOINT_SUFFIXES}

# CES-D item 10 (considered suicide) / item 21 (thought about death), stored as
# P<mm>CES10 / P<mm>CES21.
_PREFIX_ITEM_RE = re.compile(r"^P(?P<mm>00|06|12|18|24|48|96)CES(?P<item>10|21)$")
_PREFIX_ITEM_NAMES = {"10": "cesd_item_considered_suicide", "21": "cesd_item_thought_about_death"}

# Repeated measures the <stem><mm> rule cannot see, either because the name
# carries no timepoint at all or because it encodes one in a different shape.
# Every wave here was read off the per-wave codebooks in
# "Codebook_Wells et al. (2000)/PIC PAQ<mm> Codebook.pdf", which is the only
# place the timing of the unsuffixed names is recorded.
#
#   raw column -> (stem, follow_up_months)
_IRREGULAR_TIME_VARYING = {
    # Standard 20-item CES-D, collected at month 18 only ("... - PAQ18").
    "CESD1820": ("CESD20", 18),
    # 4+ counselling visits: PAQ48 calls it QNTITY50, PAQ96 QNTITY96. The 96
    # name resolves through the suffix rule on its own; only the 48 needs help.
    "QNTITY50": ("QNTITY", 48),
    # "Took any antidepressant 2+ months in past 6 months", PAQ48 / PAQ96.
    "AR482MOS": ("ANTIDEP2MOS", 48),
    "A962MOS": ("ANTIDEP2MOS", 96),
    # Utility scores appear in PAQ12 (unsuffixed) and PAQ24 (_24 suffix). Both
    # sides need an entry: without one the unsuffixed name looks time-invariant
    # and the _24 name splits off into a separate "UTILITY1_" stem.
    "UTILITY1": ("UTILITY1", 12),
    "UTILITY1_24": ("UTILITY1", 24),
    "UTILIT1N": ("UTILIT1N", 12),
    "UTILIT1N_24": ("UTILIT1N", 24),
    "UTILITY2": ("UTILITY2", 12),
    "UTILITY2_24": ("UTILITY2", 24),
    "UTILIT2N": ("UTILIT2N", 12),
    "UTILIT2N_24": ("UTILIT2N", 24),
}

# Genuinely time-invariant columns whose names end in a digit. Listing them
# keeps the guard in ``_classify_columns`` meaningful: any *other* static column
# ending in a digit is a name this loader has not been taught to read, and is
# far more likely to be an unrecognised repeated measure than a baseline
# characteristic.
_KNOWN_STATIC_ENDING_IN_DIGIT = {
    "CHRONDS3",  # 0:0 1:1 2:2 3:3+ chronic diseases (screener)
    "MAJDEP3",  # CIDI00 depression classification, 5 levels
    "MAJDEP4",  # CIDI00 depression classification, 4 levels
}

# The bare ``MCS12`` / ``PCS12`` are the *screener* SF-12 scores; the
# longitudinal SF-12 is ``MCS12<mm>`` / ``PCS12<mm>``. Rename the screener
# versions up front so the stem ``MCS12`` does not collide.
_SCREENER_RENAMES = {"MCS12": "MCS12_screener", "PCS12": "PCS12_screener"}


def _split_suffix(col: str) -> tuple[str, int] | None:
    """Split a regular ``<stem><mm>`` repeated-measure name."""
    for suffix in TIMEPOINT_SUFFIXES:
        if col.endswith(suffix) and len(col) > len(suffix):
            return col[: -len(suffix)], SUFFIX_TO_MONTHS[suffix]
    return None


def _classify_column(col: str) -> tuple[str, int] | None:
    """Return ``(stem, months)`` for a repeated measure, or ``None`` if static."""
    if col in _IRREGULAR_TIME_VARYING:
        return _IRREGULAR_TIME_VARYING[col]

    item_match = _PREFIX_ITEM_RE.match(col)
    if item_match:
        return _PREFIX_ITEM_NAMES[item_match.group("item")], int(item_match.group("mm"))

    return _split_suffix(col)


def load() -> pd.DataFrame:
    ensure_unzipped(
        zip_path=_STUDY_DIR / "31_Wells_Trial.zip",
        extract_dir=_STUDY_DIR,
        marker_path=_MARKER,
    )
    df = pd.read_spss(_MARKER, convert_categoricals=False)
    if df.columns.duplicated().any():
        duplicated = sorted(set(df.columns[df.columns.duplicated()]))
        raise ValueError(f"Duplicate column name(s) in the source file: {duplicated}")
    df = df.convert_dtypes()
    df = df.rename(columns={k: v for k, v in _SCREENER_RENAMES.items() if k in df.columns})

    missing_id = df[ID_COL].isna()
    if missing_id.any():
        logger.warning(f"Dropped {int(missing_id.sum())} rows with missing {ID_COL}.")
        df = df.loc[~missing_id]

    duplicated_id = df[ID_COL].duplicated(keep=False)
    if duplicated_id.any():
        logger.warning(f"Dropped {int(duplicated_id.sum())} rows with duplicated {ID_COL}.")
        df = df.loc[~duplicated_id]

    # (stem, months) -> raw column
    time_varying: dict[tuple[str, int], str] = {}
    static_cols = [ID_COL]
    for col in df.columns:
        if col == ID_COL:
            continue
        parsed = _classify_column(col)
        if parsed is None:
            static_cols.append(col)
            continue
        if parsed in time_varying:
            raise ValueError(
                f"{col!r} and {time_varying[parsed]!r} both resolve to {parsed}; "
                f"one of them is classified wrongly."
            )
        time_varying[parsed] = col

    unclassified = [
        col
        for col in static_cols
        if col[-1:].isdigit() and col not in _KNOWN_STATIC_ENDING_IN_DIGIT
    ]
    if unclassified:
        raise ValueError(
            f"Column(s) {sorted(unclassified)} end in a digit but were treated as "
            f"time-invariant. Check the PIC PAQ<mm> codebooks and add them to "
            f"_IRREGULAR_TIME_VARYING or _KNOWN_STATIC_ENDING_IN_DIGIT."
        )

    all_months = sorted(set(SUFFIX_TO_MONTHS.values()))
    frames = []
    for months in all_months:
        renames = {col: stem for (stem, m), col in time_varying.items() if m == months}
        clash = set(renames.values()) & set(static_cols)
        if clash:
            raise ValueError(f"time-varying stem(s) collide with a static column: {sorted(clash)}")
        visit = df[static_cols + list(renames)].rename(columns=renames)
        visit.insert(1, "follow_up_months", months)
        frames.append(visit)

    long = (
        pd.concat(frames, ignore_index=True, sort=False)
        .rename(columns={ID_COL: "patient_id"}, errors="raise")
        .sort_values(["patient_id", "follow_up_months"], kind="stable")
        .reset_index(drop=True)
    )

    if long.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    head = ["patient_id", "follow_up_months"]
    return long[head + [c for c in long.columns if c not in head]].convert_dtypes()
