import zipfile

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
    """Extract only the CLEANED SPSS file.

    ``27_Rollman_2009.zip`` contains an unrelated corrupt member, so a plain
    ``extractall`` raises. Extracting just the one file we need avoids it.
    """
    if _EXTRACT_MARKER.exists():
        return
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
# "assessed" boxes; Depres_0's pooled mean (12.0) and per-arm baseline means
# match Table 1, and Depres_f4's per-arm means match the Table 2 8-month row.
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
    df = pd.read_spss(_EXTRACT_MARKER, convert_categoricals=False).convert_dtypes()
    df = df.rename(columns={"Origpat_id": "patient_id"}, errors="raise")

    assert df["patient_id"].notna().all(), "Rows with missing patient_id"
    if df["patient_id"].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    static_present = [c for c in TIME_INDEPENDENT_COLS if c in df.columns]
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
