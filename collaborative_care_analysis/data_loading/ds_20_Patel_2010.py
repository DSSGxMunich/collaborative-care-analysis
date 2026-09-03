import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Patel 2010 = the MANAS trial (Lancet 2010;376:2086-95). Cluster RCT, 24
# primary-care facilities in Goa, India (12 public + 12 private), assigned 1:1
# to a collaborative stepped-care intervention led by a lay health counsellor
# (case management + psychosocial treatment + antidepressants by the PCP +
# mental-health-specialist supervision) vs enhanced usual care. Screen-positive
# adults with a common mental disorder were recruited. Primary outcome: recovery
# from an ICD-10 common mental disorder at 6 months; further assessments at
# 2 and 12 months.
#
# ``Patel 2001.pdf`` is a mislabelled duplicate of ``Patel 2010.pdf`` (same
# MANAS paper). This loader uses ``Patel 2001 CLEANED.sav`` (774 rows) -- the
# curated file in the standardised meta-analysis schema; it appears to be the
# ICD-10 *depression* subgroup rather than the full CMD sample in
# ``Patel clean.sav`` (2246 rows). SEE NOTE in notes/ds_20_Patel_2010.md --
# the 774-vs-2246 choice should be confirmed with the study team.
#
# The file is wide: baseline columns end in ``_b`` or ``_0``; the three review
# waves end in ``_r1``/``_f1`` (2 months), ``_r2``/``_f3`` (6 months) and
# ``_r3``/``_f5`` (12 months). This loader stacks them into long format.

_STUDY_DIR = RAW_DATASETS_DIR / "20_Patel_2010"

ID_COL = "Origpat_id"

# (suffixes that mark this wave, follow_up_months). Order matters: longer /
# more specific suffixes are checked first.
WAVE_SUFFIXES = [
    (("_f1", "_r1"), 2),
    (("_f3", "_r2"), 6),
    (("_f5", "_r3"), 12),
    (("_0", "_b"), 0),
]

TIME_INDEPENDENT_COLS = ["Cluster_id", "group", "Sex", "Age"]

# Trial-level metadata columns (constant for every row); dropped.
_METADATA_COLS = {
    "TriaI_id",
    "Time",
    "DepresSev_Mes",
    "DepresD_Mes",
    "LTC_Mes",
    "LTC_incl",
    "LTC_inclType",
    "LTC_emp",
    "Medadh_Mes",
    "Satcare_Mes",
    "Compl_Mes",
    "VAR00078",
    "VAR00079",
}


def _split_suffix(col: str) -> tuple[str, int] | None:
    for suffixes, months in WAVE_SUFFIXES:
        for suffix in suffixes:
            if col.endswith(suffix) and len(col) > len(suffix):
                return col[: -len(suffix)], months
    return None


def load(file_path=_STUDY_DIR / "Patel 2001 CLEANED.sav") -> pd.DataFrame:
    df = pd.read_spss(file_path, convert_categoricals=False).convert_dtypes()
    df = df.drop(columns=[c for c in _METADATA_COLS if c in df.columns])
    df = df.rename(columns={ID_COL: "patient_id"}, errors="raise")

    assert df["patient_id"].notna().all(), "Rows with missing patient_id"
    if df["patient_id"].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    static_cols = ["patient_id", *[c for c in TIME_INDEPENDENT_COLS if c in df.columns]]

    # stem -> {months: raw column}
    time_varying: dict[str, dict[int, str]] = {}
    for col in df.columns:
        if col in static_cols:
            continue
        parsed = _split_suffix(col)
        if parsed is None:
            raise ValueError(f"Column has no recognised wave suffix: {col!r}")
        stem, months = parsed
        time_varying.setdefault(stem, {})[months] = col

    collisions = set(time_varying) & set(static_cols)
    if collisions:
        raise ValueError(f"stem also used as a static column: {sorted(collisions)}")

    all_months = [0, 2, 6, 12]
    frames = []
    for months in all_months:
        renames = {
            by_month[months]: stem for stem, by_month in time_varying.items() if months in by_month
        }
        visit = df[static_cols + list(renames)].rename(columns=renames)
        visit.insert(1, "follow_up_months", months)
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
