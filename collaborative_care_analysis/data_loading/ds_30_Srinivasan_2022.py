import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Srinivasan 2022 = the HOPE trial: a cluster-randomised trial of collaborative
# care for depression and cardiovascular risk in rural primary health centres
# (PHCs) in Karnataka, India. ``treatarm`` 0 = usual care, 1 = collaborative
# care. Patients assessed at baseline and 3, 6, 12 months on PHQ-9 (depression),
# GAD-7 (anxiety), WHOQOL, blood pressure, HbA1c and lipids.
#
# The raw file is one wide row per patient with every measure suffixed by its
# month (``_0`` / ``_3`` / ``_6`` / ``_12``). This loader stacks those into long
# format; columns with no month suffix are time-invariant.

_STUDY_DIR = RAW_DATASETS_DIR / "30_Srinivasan_2022"

ID_COL = "Participant"

# longest-first so "_12" is tried before "_1" would be (there is no "_1", but
# this keeps the rule explicit and safe).
SUFFIX_TO_MONTHS = {"_12": 12, "_0": 0, "_3": 3, "_6": 6}


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    time_varying: dict[str, dict[int, str]] = {}
    for col in df.columns:
        if col == ID_COL:
            continue
        for suffix, months in SUFFIX_TO_MONTHS.items():
            if col.endswith(suffix):
                time_varying.setdefault(col[: -len(suffix)], {})[months] = col
                break

    matched = {c for m in time_varying.values() for c in m.values()}
    static_cols = [c for c in df.columns if c != ID_COL and c not in matched]

    collisions = set(time_varying) & set(static_cols)
    if collisions:
        raise ValueError(f"stem also used as a static column: {sorted(collisions)}")

    frames = []
    for months in sorted(set(SUFFIX_TO_MONTHS.values())):
        renames = {
            by_month[months]: stem for stem, by_month in time_varying.items() if months in by_month
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
    return long[head + [c for c in long.columns if c not in head]]


def load(
    file_path=_STUDY_DIR / "HOPE vars for MA all waves, no ID.sav",
) -> pd.DataFrame:
    df = pd.read_spss(file_path, convert_categoricals=False).convert_dtypes()

    assert df[ID_COL].notna().all(), "Rows with missing Participant id"
    if df[ID_COL].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    return to_long(df).convert_dtypes()
