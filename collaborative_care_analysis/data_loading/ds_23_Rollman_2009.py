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


# Standardised HRSD severity column -> follow_up_months, using the codebook's
# own "Time" labels (f1 = "1-2 months", f2 = "3-4 months", f4 = "8-9 months",
# f5 = "12 months", f6 = "18 months", f7 = "24 months", f8 = "36 months";
# f7.5 sits between 24 and 36 -> approximated as 30).
DEPRES_TO_MONTHS = {
    "Depres_0": 0,
    "Depres_f1": 2,
    "Depres_f2": 4,
    "Depres_f4": 8,
    "Depres_f5": 12,
    "Depres_f6": 18,
    "Depres_f7": 24,
    "Depres_f7.5": 30,
    "Depres_f8": 36,
}

# HRSD suicide item T2..T10 lines up with the Depres_* series above (matched by
# non-null counts: T2<->Depres_0, T4<->Depres_f2, T8<->Depres_f7, T10<->Depres_f8).
HSRDSUIC_TO_MONTHS = dict(
    zip(
        [
            "HSRDsuic_T2",
            "HSRDsuic_T3",
            "HSRDsuic_T4",
            "HSRDsuic_T5",
            "HSRDsuic_T6",
            "HSRDsuic_T7",
            "HSRDsuic_T8",
            "HSRDsuic_T9",
            "HSRDsuic_T10",
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
