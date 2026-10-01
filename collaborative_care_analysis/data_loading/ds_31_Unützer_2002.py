from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Unützer 2002 = the IMPACT trial (JAMA 2002;288:2836-2845): "Collaborative Care
# Management of Late-Life Depression in the Primary Care Setting." 18 primary
# care clinics across 8 US health-care organisations. N = 1801 adults >= 60 with
# major depression and/or dysthymia. IMPACT collaborative care (a depression care
# manager offering problem-solving treatment and/or antidepressant support,
# stepped care, psychiatrist supervision) vs usual care. Primary outcome:
# depression severity (SCL-20, mean of 20 items, 0-4). ``RAND`` 1 = intervention
# (n=906), 0 = usual care (n=895), matching the paper, whose mean age 71.2 (7.5)
# and 1168 women this file also reproduces exactly.
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
    # blank/whitespace-only cells are missing, before any dtype work
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)

    incomplete = df[ID_COL].isna() | df["RAND"].isna()
    if incomplete.any():
        logger.warning(f"Dropped {int(incomplete.sum())} rows with missing {ID_COL} or RAND.")
        df = df.loc[~incomplete]

    duplicated_id = df[ID_COL].duplicated(keep=False)
    if duplicated_id.any():
        logger.warning(f"Dropped {int(duplicated_id.sum())} rows with duplicated {ID_COL}.")
        df = df.loc[~duplicated_id]

    static_present = [c for c in TIME_INDEPENDENT_COLS if c in df.columns]
    if absent := [c for c in TIME_INDEPENDENT_COLS if c not in df.columns]:
        logger.warning(f"Declared time-independent column(s) absent from the export: {absent}")

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
