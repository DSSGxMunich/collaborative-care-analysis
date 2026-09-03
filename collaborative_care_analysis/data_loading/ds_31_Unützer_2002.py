import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Unützer 2002 = the IMPACT trial (JAMA 2002;288:2836-2845): "Collaborative Care
# Management of Late-Life Depression in the Primary Care Setting." 18 primary
# care clinics across 8 US health-care organisations. N = 1801 adults >= 60 with
# major depression and/or dysthymia. IMPACT collaborative care (a depression care
# manager offering problem-solving treatment and/or antidepressant support,
# stepped care, psychiatrist supervision) vs usual care. Primary outcome:
# depression severity (SCL-20, mean of 20 items, 0-4).
#
# ``Unutzer_2002.csv`` is the curated file matching the documented IPD variable
# list (see "IMPACT_List of variables for the IPD analyses"); it carries SCL-20
# at baseline, 6 and 12 months. The broader "Impact depression severity study 2"
# files are missing several IPD variables and are not used.

_STUDY_DIR = RAW_DATASETS_DIR / "31_Unützer_2002"

ID_COL = "aid"

TIME_INDEPENDENT_COLS = [
    "RAND",
    "AGE",
    "RACE2",
    "DIAG00",
    "female",
    "NUMDIS2",
    "ARTHRIT",
    "BLADDER",
    "CANCER",
    "HEART",
    "HEARVIS",
    "HIGHBP",
    "LUNG",
    "NEURO",
    "STOMACH",
    "DIAB",
]

# harmonised stem -> {follow_up_months: raw column}
FAMILIES = {
    "scl20_mean": {0: "SCL00", 6: "scl06", 12: "scl12"},
    "scl_item12": {0: "SCL1200", 6: "SCL1206", 12: "SCL1212"},
    "scl_item13": {0: "SCL1300", 6: "SCL1306", 12: "SCL1312"},
}


def load(file_path=_STUDY_DIR / "Unutzer_2002.csv") -> pd.DataFrame:
    df = pd.read_csv(file_path)

    assert df[ID_COL].notna().all(), "Rows with missing aid"
    if df[ID_COL].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    static_present = [c for c in TIME_INDEPENDENT_COLS if c in df.columns]

    frames = []
    for months in (0, 6, 12):
        visit = df[[ID_COL, *static_present]].copy()
        visit.insert(1, "follow_up_months", months)
        for stem, by_month in FAMILIES.items():
            col = by_month.get(months)
            if col in df.columns:
                visit[stem] = df[col]
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
