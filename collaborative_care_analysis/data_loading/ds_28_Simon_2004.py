import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

# Simon 2004 = "Telephone psychotherapy and telephone care management for
# primary care patients starting antidepressant treatment" (JAMA 2004;292:935-
# 942). 3-arm RCT, N = 600: usual care (0), telephone care management (1),
# telephone care management + telephone CBT (2). Depression severity = SCL-20
# (mean of 20 items, 0-4), assessed at baseline, 6 weeks, 3 months, 6 months
# (per the dataset codebook).

_STUDY_DIR = RAW_DATASETS_DIR / "28_Simon_2004"

# standardised column -> follow_up_months (codebook: f1 = "6 Wochen",
# f2 = "3 Monate", f3 = "6 Monate"). 6 weeks -> 1.5 months.
DEPRES_TO_MONTHS = {
    "Depres_0": 0.0,
    "Depres_f1": 1.5,
    "Depres_f2": 3.0,
    "Depres_f3": 6.0,
}

TIME_INDEPENDENT_COLS = ["group", "age", "Sex"]


def load(file_path=_STUDY_DIR / "simon2004.CLEANEDsav.sav") -> pd.DataFrame:
    df = pd.read_spss(file_path, convert_categoricals=False).convert_dtypes()
    # Treat blank or whitespace-only strings as missing values.
    df = df.replace(
        to_replace=r"^\s*$",
        value=pd.NA,
        regex=True,
    )

    df = df.rename(columns={"Origpat_id": "patient_id"}, errors="raise")

    assert df["patient_id"].notna().all(), "Rows with missing patient_id"
    if df["patient_id"].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    id_vars = ["patient_id", *TIME_INDEPENDENT_COLS]
    long_df = df[id_vars + list(DEPRES_TO_MONTHS)].melt(
        id_vars=id_vars,
        value_vars=list(DEPRES_TO_MONTHS),
        var_name="_col",
        value_name="scl20_mean",
    )
    long_df["follow_up_months"] = map_with_check(long_df["_col"], DEPRES_TO_MONTHS)
    long_df = long_df.drop(columns="_col")

    if long_df.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    long_df = long_df.sort_values(["patient_id", "follow_up_months"]).reset_index(drop=True)
    head = ["patient_id", "follow_up_months"]
    return long_df[head + [c for c in long_df.columns if c not in head]].convert_dtypes()
