import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Salisbury 2016 = the Healthlines Depression trial (Lancet Psychiatry
# 2016;3:515-25). Pragmatic multicentre RCT, 43 English GP practices. Adults
# with a confirmed depression diagnosis and PHQ-9 >= 10, internet + email
# access, individually assigned 1:1 to the Healthlines Depression Service
# (telehealth advisers + web content, on top of usual care) vs usual care alone.
# N = 609. Primary outcome: PHQ-9 response at 4 months. Assessments at baseline,
# 4, 8, 12 months.
#
# ``allocation`` 1 = usual care, 2 = Healthlines intervention (inferred: the
# intervention-only "was the blood-pressure webpage helpful/easy" items are
# answered almost entirely by allocation 2).
#
# The raw CSV is wide, every repeated measure suffixed ``_0``/``_4``/``_8``/
# ``_12`` (= months). This loader stacks them into long format.

_CSV = RAW_DATASETS_DIR / "26_Salisbury_2016" / "Healthlines_Depression_trial_data.csv"

# Stata-style extended missing codes present in the CSV.
_NA_VALUES = [".", ".a", ".b", ".c", ".d", ".e"]

SUFFIX_TO_MONTHS = {"_0": 0, "_4": 4, "_8": 8, "_12": 12}

TIME_INDEPENDENT_COLS = [
    "allocation",
    "randomisation_date",
    "site",
    "practice_id",
    "phq9_categorical",
    "age_categorical",
    "imdscore_home",
]


def load() -> pd.DataFrame:
    df = pd.read_csv(_CSV, na_values=_NA_VALUES)

    assert df["id"].notna().all(), "Rows with missing id"
    if df["id"].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    static_cols = ["id", *[c for c in TIME_INDEPENDENT_COLS if c in df.columns]]

    # stem -> {months: raw column}
    time_varying: dict[str, dict[int, str]] = {}
    for col in df.columns:
        if col in static_cols:
            continue
        for suffix, months in SUFFIX_TO_MONTHS.items():
            if col.endswith(suffix):
                time_varying.setdefault(col[: -len(suffix)], {})[months] = col
                break
        else:
            raise ValueError(f"Column has no recognised timepoint suffix: {col!r}")

    frames = []
    for months in SUFFIX_TO_MONTHS.values():
        renames = {
            by_month[months]: stem for stem, by_month in time_varying.items() if months in by_month
        }
        visit = df[static_cols + list(renames)].rename(columns=renames)
        visit.insert(1, "follow_up_months", months)
        frames.append(visit)

    long = (
        pd.concat(frames, ignore_index=True, sort=False)
        .rename(columns={"id": "patient_id"}, errors="raise")
        .sort_values(["patient_id", "follow_up_months"], kind="stable")
        .reset_index(drop=True)
    )

    if long.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    # Drop rows with non-integer PHQ-9/GAD-7 totals (e.g. 5.7, 14.625 —
    # not valid Likert-summed scores).
    for col in ["phq9_total", "gad7_total"]:
        if col in long.columns:
            long = long[~(pd.to_numeric(long[col], errors="raise") % 1 > 0)]

    head = ["patient_id", "follow_up_months"]
    return long[head + [c for c in long.columns if c not in head]].convert_dtypes()
