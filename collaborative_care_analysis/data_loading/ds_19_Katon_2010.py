import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Katon 2010 = the TEAMcare trial (NEJM 2010;363:2611-2620). Single-blind RCT,
# 14 primary-care clinics (Group Health, Seattle). N = 214 patients with
# depression AND poorly controlled diabetes and/or coronary heart disease.
# Intervention = a nurse care manager, supervised by physicians, treating
# depression and the medical disease targets to goal; control = usual care.
# SCL-20 depression and WHODAS function assessed over 24 months (the main paper
# reports 6/12-month outcomes; longer follow-up in Katon 2012).
#
# This loader uses the raw ``KATON TEAMCARE.sav`` (its codebook states the
# timepoints explicitly). The "Katon teamcare.CLEANED.sav" is the standardised
# meta-analysis schema, whose ``Depres_*`` slots were unreliable for the sister
# study ds_18, so the raw file is preferred here too.

_STUDY_DIR = RAW_DATASETS_DIR / "19_Katon_2010"

ID_COL = "id"

TIME_INDEPENDENT_COLS = [
    "intervention",
    "Aage",
    "SEX",
    "DIABETIC",
    "HEARTDIS",
    "A4",  # Hispanic/Latino
    "A5_5",
    "A5_1",
    "A5_2",
    "A5_3",
    "A5_4",
    "A5_6",  # race
    "AAntidepAdhere",  # antidepressant adherence, 12 mo pre-baseline
    "CAntidepAdhere",  # antidepressant adherence, baseline-12 mo
]

# stem -> {follow_up_months: raw column name}. From the dataset codebook
# ("FOLLOW 1" = 6 months, ... "FOLLOW 4" = 24 months).
REPEATED_MEASURES = {
    "scl20_mean": {0: "aSCL", 6: "BSCL", 12: "CSCL", 18: "DSCL", 24: "ESCL"},
    "whodas_total": {0: "AWhodasTotal", 6: "BWhodasTotal", 12: "CWhodasTotal"},
    "whodas_getting_around": {
        0: "AWhodasGettingAround",
        6: "BWhodasGettingAround",
        12: "CWhodasGettingAround",
    },
    "whodas_self_care": {0: "AWHODASSelfCare", 6: "bWHODASSelfCare", 12: "cWHODASSelfCare"},
    "whodas_household": {0: "AWHODASHousehold", 6: "BWHODASHousehold", 12: "CWHODASHousehold"},
    "satisfaction_diabetes_care": {0: "A51", 6: "B51", 12: "C51", 18: "D51", 24: "E51"},
    "satisfaction_heart_disease_care": {0: "A55", 6: "B55", 12: "C55", 18: "D55", 24: "E55"},
    "satisfaction_depression_care": {6: "B111", 12: "C111", 18: "D111", 24: "E111"},
}

ALL_MONTHS = sorted({m for mapping in REPEATED_MEASURES.values() for m in mapping})


def load(file_path=_STUDY_DIR / "KATON TEAMCARE.sav") -> pd.DataFrame:
    df = pd.read_spss(file_path).convert_dtypes()
    df = df.rename(columns={ID_COL: "patient_id"}, errors="raise")

    assert df["patient_id"].notna().all(), "Rows with missing patient_id"
    if df["patient_id"].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    static_present = [c for c in TIME_INDEPENDENT_COLS if c in df.columns]

    frames = []
    for months in ALL_MONTHS:
        visit = df[["patient_id", *static_present]].copy()
        visit.insert(1, "follow_up_months", months)
        for stem, by_month in REPEATED_MEASURES.items():
            col = by_month.get(months)
            if col is not None:
                visit[stem] = df[col]
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
