import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Davidson 2013 = the CODIACS Vanguard RCT. Patients recruited 2-6 months after
# an acute coronary syndrome with Beck Depression Inventory (BDI-I) score >=10;
# randomised 1:1 to "Stepped Care" (centralised, stepped, patient-preference
# depression care: problem-solving therapy and/or pharmacotherapy) vs "Referred
# Care" (local physician). N = 150. BDI, health-care use and medication use were
# assessed at baseline and 6 months in person and at 2 and 4 months by phone.
# Primary outcomes: change in BDI over 6 months and health-care costs.
#
# The raw file is wide: one row per patient, repeated measures encoded as column
# suffixes ``_bl`` / ``_2m`` / ``_4m`` / ``_6m``. This loader stacks those into
# long format (one row per patient-visit). Columns with no timepoint suffix are
# treated as time-invariant and broadcast to every visit row.

ID_COL = "SUBJID"

SUFFIX_TO_MONTHS = {
    "_bl": 0,
    "_2m": 2,
    "_4m": 4,
    "_6m": 6,
}


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Stack the ``_bl`` / ``_2m`` / ``_4m`` / ``_6m`` visits into long format."""
    # stem -> {suffix: column name}
    time_varying: dict[str, dict[str, str]] = {}
    for col in df.columns:
        if col == ID_COL:
            continue
        for suffix in SUFFIX_TO_MONTHS:
            if col.endswith(suffix):
                time_varying.setdefault(col[: -len(suffix)], {})[suffix] = col
                break

    matched = {c for mapping in time_varying.values() for c in mapping.values()}
    static_cols = [c for c in df.columns if c != ID_COL and c not in matched]

    collisions = set(time_varying) & set(static_cols)
    if collisions:
        raise ValueError(f"stem name also used as a static column: {sorted(collisions)}")

    frames = []
    for suffix, months in SUFFIX_TO_MONTHS.items():
        # Only carry stems that were actually measured at this visit; pd.concat
        # aligns on column name and fills the rest with NaN.
        renames = {
            by_suffix[suffix]: stem
            for stem, by_suffix in time_varying.items()
            if suffix in by_suffix
        }
        visit = df[[ID_COL, *static_cols, *renames]].rename(columns=renames)
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


def load(file_path=RAW_DATASETS_DIR / "09_Davidson_2013" / "Davidson 2013 CLEANED.sav"):
    df = pd.read_spss(file_path, convert_categoricals=False).convert_dtypes()

    assert df[ID_COL].notna().all(), "Rows with missing SUBJID"
    if df[ID_COL].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    return to_long(df)
