import zipfile

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Rollman 2009 = the "Bypassing the Blues" trial (JAMA 2009;302:2095-2103):
# telephone-delivered collaborative care for depression after coronary artery
# bypass graft (CABG) surgery vs usual care. 302 depressed patients randomised
# (150 collaborative care / 152 usual care) plus a 151-patient non-depressed
# comparison cohort (n = 453 total). Primary outcomes: HRSD (Hamilton Rating
# Scale for Depression) and SF-36 mental-component score at 8 months.
#
# IMPORTANT: the previous loader read "OT Meta Data_ Munich.xlsx" from the
# shared OT/RELAX archive -- that is the *OT trial* (Rollman 2017, ds_25), NOT
# Bypassing the Blues. The real Rollman 2009 data lives in
# ``27_Rollman_2009.zip``, extracted here.

_STUDY_DIR = RAW_DATASETS_DIR / "23_Rollman_2009"
_ZIP_PATH = _STUDY_DIR / "27_Rollman_2009.zip"
_MEMBER = "Rollman 2009/Rollman 2009 CLEANED.sav"
_EXTRACT_MARKER = _STUDY_DIR / _MEMBER


def _ensure_extracted() -> None:
    """Make sure the CLEANED SPSS file is present.

    The study folder no longer carries ``27_Rollman_2009.zip`` -- the extracted
    ``Rollman 2009/`` directory is what is there now -- so this normally does
    nothing. The extraction path is kept for a folder that still has the zip,
    and pulls out the single member we need because the archive also contains
    an unrelated corrupt one that makes ``extractall`` raise.
    """
    if _EXTRACT_MARKER.exists():
        return
    if not _ZIP_PATH.exists():
        raise FileNotFoundError(
            f"{_EXTRACT_MARKER} is missing, and {_ZIP_PATH.name} is not in the study "
            "folder to extract it from."
        )
    with zipfile.ZipFile(_ZIP_PATH) as zf:
        zf.extract(_MEMBER, _STUDY_DIR)


# Standardised HRSD severity column -> follow_up_months.
#
# Bypassing the Blues assessed the HRS-D at baseline and at 2-, 4-, and 8-month
# follow-up only (JAMA 2009;302:2095-2103, Methods: "at 2 weeks and at 2-, 4-,
# and 8-month follow-up"; the analysis model uses "time (4 time points)"; the
# CONSORT figure has no assessment box past 8 months, and recruitment ran only
# Mar 2004 - Sep 2007 with observation ending Jun 2008). The per-arm non-null
# counts of Depres_f1 / f2 / f4 line up with the figure's 2- / 4- / 8-month
# "assessed" boxes (121/136 at 2 months and 135 usual care at 4 months are
# exact, the rest within two patients), and the per-arm means match Table 2's
# HRS-D rows: baseline 16.55 / 15.92 against the reported 16.6 / 16.0, and
# Depres_f4 8.92 for the intervention arm against the reported 9.0.
#
# The .sav *also* carries Depres_f5 / f6 / f7 / f7.5 / f8. These are NOT part of
# the trial: nothing in the paper accounts for them, their per-arm behaviour is
# inconsistent with the published result (at f8 the intervention arm scores
# worse than usual care), and the only source for a 12 / 18 / 24 / 36-month
# reading is the generic "Time" grid in the shared meta-analysis codebook
# (whose TriaI_id is even labelled "Bruce 2004"). We drop them rather than
# harmonise fabricated long-horizon waves into the merged dataset.
DEPRES_TO_MONTHS = {
    "Depres_0": 0,
    "Depres_f1": 2,
    "Depres_f2": 4,
    "Depres_f4": 8,
}

# HRSD suicide item: T2..T5 line up with the Depres_* series above (matched by
# non-null counts: T2<->Depres_0, T3<->Depres_f1, T4<->Depres_f2, T5<->Depres_f4).
# T6..T10 are the suicide-item counterparts of the out-of-scope Depres_f5..f8
# waves and are dropped for the same reason.
HSRDSUIC_TO_MONTHS = dict(
    zip(
        [
            "HSRDsuic_T2",
            "HSRDsuic_T3",
            "HSRDsuic_T4",
            "HSRDsuic_T5",
        ],
        DEPRES_TO_MONTHS.values(),
    )
)

TIME_INDEPENDENT_COLS = [
    "Group",
    "Sex",
    "Age",
    "Ethnic",
    "LTC_0",
    "LTCn_0",
    "HPT_0",
    "DM_0",
    "HLD_0",
    "CVA_0",
    "COPD_0",
    "Renal_0",
    "MI_0",
    "CHF_0",
]

FAMILIES = {
    "hrsd17_total": DEPRES_TO_MONTHS,
    "hrsd17_suicide_item": HSRDSUIC_TO_MONTHS,
}


def load() -> pd.DataFrame:
    _ensure_extracted()
    df = pd.read_spss(_EXTRACT_MARKER, convert_categoricals=False)
    # treat blank or whitespace-only strings as missing, before dtype inference
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)
    df = df.convert_dtypes()
    df = df.rename(columns={"Origpat_id": "patient_id"}, errors="raise")

    incomplete = df["patient_id"].isna() | df["Group"].isna()
    if incomplete.any():
        logger.warning(f"Dropped {int(incomplete.sum())} rows with missing patient_id or Group.")
        df = df.loc[~incomplete]

    duplicated_id = df["patient_id"].duplicated(keep=False)
    if duplicated_id.any():
        logger.warning(f"Dropped {int(duplicated_id.sum())} rows with duplicated patient_id.")
        df = df.loc[~duplicated_id]

    # Keep only the randomised arms: Group 1 is collaborative care and 0 usual
    # care (the file's value labels confirm "Intervention"/"Control"), while 3
    # is the non-depressed comparison cohort, which was never randomised.
    comparison_cohort = df["Group"] == 3
    if comparison_cohort.any():
        logger.info(
            f"Dropped {int(comparison_cohort.sum())} non-depressed comparison-cohort rows "
            "(Group == 3), which were not randomised."
        )
    df = df.loc[~comparison_cohort].reset_index(drop=True)

    static_present = [c for c in TIME_INDEPENDENT_COLS if c in df.columns]
    if absent := [c for c in TIME_INDEPENDENT_COLS if c not in df.columns]:
        logger.warning(f"Declared time-independent column(s) absent from the export: {absent}")
    all_months = sorted(set(DEPRES_TO_MONTHS.values()))

    frames = []
    for months in all_months:
        visit = df[["patient_id", *static_present]].copy()
        visit.insert(1, "follow_up_months", months)
        for stem, col_to_months in FAMILIES.items():
            cols = [c for c, m in col_to_months.items() if m == months and c in df.columns]
            if cols:
                visit[stem] = df[cols[0]]
        frames.append(visit)

    long = (
        pd.concat(frames, ignore_index=True, sort=False)
        .sort_values(["patient_id", "follow_up_months"], kind="stable")
        .reset_index(drop=True)
    )

    if long.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    head = ["patient_id", "follow_up_months"]
    return long[head + [c for c in long.columns if c not in head]].convert_dtypes()
