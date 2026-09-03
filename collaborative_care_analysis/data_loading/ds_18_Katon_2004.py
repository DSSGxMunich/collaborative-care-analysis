import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

# Katon 2004 = the Pathways Study: RCT of collaborative care (nurse care manager,
# problem-solving therapy and/or antidepressant support, supervised by a
# psychiatrist) vs. usual care in primary-care patients with diabetes and
# comorbid depression. N = 329. SCL-20 depression severity assessed at
# baseline, 3, 6, 9 and 12 months (per the dataset codebook).
#
# DATA NOTE: the file also carries a "standardised" ``Depres_0 / Depres_f2..f5``
# series, but it is off by one -- ``Depres_0`` equals the raw ``cscl`` (the
# 3-month reading), not the true baseline, and ``Depres_f5`` has no raw
# counterpart. The raw ``bscl/cscl/dscl/escl/fscl`` columns ("SCL - Avg of C8a
# through C8t", i.e. the mean of the 20 depression items, 0-4) are the source of
# truth and include the true baseline (``bscl``, 329/329 non-null). This loader
# uses the raw series; the ``Depres_*`` columns are dropped.

SCL_TO_MONTHS = {
    "bscl": 0,
    "cscl": 3,
    "dscl": 6,
    "escl": 9,
    "fscl": 12,
}

_STANDARDISED_COLS = ["Depres_0", "Depres_f2", "Depres_f3", "Depres_f4", "Depres_f5"]

TIME_INDEPENDENT_COLS = ["Group", "Age", "Sex", "LTC_0", "LTCsev_0"]


def load(file_path=RAW_DATASETS_DIR / "18_Katon_2004" / "katon2004.sav"):
    df = pd.read_spss(file_path).convert_dtypes()

    df = df.rename(columns={"Origpat_id": "patient_id"}, errors="raise")

    assert df["patient_id"].notna().all(), "Rows with missing patient_id"
    if df["patient_id"].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    value_vars = list(SCL_TO_MONTHS)
    id_vars = ["patient_id", *TIME_INDEPENDENT_COLS]

    long_df = df[id_vars + value_vars].melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name="_scl_col",
        value_name="scl20_mean",
    )
    long_df["follow_up_months"] = map_with_check(long_df["_scl_col"], SCL_TO_MONTHS)
    long_df = long_df.drop(columns="_scl_col")

    if long_df.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    long_df = long_df.sort_values(["patient_id", "follow_up_months"]).reset_index(drop=True)
    head = ["patient_id", "follow_up_months"]
    return long_df[head + [c for c in long_df.columns if c not in head]]
