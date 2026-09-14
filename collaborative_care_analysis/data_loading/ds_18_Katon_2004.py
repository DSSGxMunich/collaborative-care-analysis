import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

# Katon 2004 = the Pathways Study: RCT of collaborative care (nurse care manager,
# problem-solving therapy and/or antidepressant support, supervised by a
# psychiatrist) vs. usual care in primary-care patients with diabetes and
# comorbid depression. N = 329. The paper's independent, blinded SCL-90
# assessments were done at baseline, 3, 6, and 12 months only (Methods:
# "telephone interviews were provided at 3, 6, and 12 months"); this loader
# keeps exactly those four waves.
#
# DATA NOTE: the file also carries a "standardised" ``Depres_0 / Depres_f2..f5``
# series, but it is off by one -- ``Depres_0`` equals the raw ``cscl`` (the
# 3-month reading), not the true baseline, and ``Depres_f5`` has no raw
# counterpart. The raw ``bscl/cscl/dscl/escl/fscl`` columns ("SCL - Avg of C8a
# through C8t", i.e. the mean of the 20 depression items, 0-4) are the source of
# truth and include the true baseline (``bscl``, 329/329 non-null). This loader
# uses the raw series; the ``Depres_*`` columns are dropped.
#
# DATA NOTE 2: the letters do NOT run baseline->12mo in alphabetical order --
# ``escl``/``fscl`` are swapped relative to that naive reading, and ``fscl`` is
# dropped entirely. Full derivation in
# notebooks/1.2-js-ds18-katon2004-followup-month-mapping.ipynb; summary,
# verified against Katon et al. 2004 (Arch Gen Psychiatry 61:1042-1049) by
# group:
#   - ``bscl`` reproduces Table 1's baseline SCL-20 mean/SD exactly (Control
#     1.63/0.454 == 1.6/0.45; Intervention 1.71/0.514 == 1.7/0.51) -> 0 months.
#   - ``cscl`` matches the paper's 3-month completer counts exactly (154 usual
#     care / 151 intervention) -> 3 months.
#   - ``dscl`` matches the 6-month completer counts (149/144 vs the paper's
#     149/143) and its mean change from ``bscl`` (0.386/0.563) matches the
#     reported 6-month change (0.39/0.56); Table 3's 6-month >=40% response
#     rates (34.2%/42.4%) match exactly -> 6 months.
#   - ``escl`` -- not ``fscl`` -- matches the 12-month completer counts exactly
#     (142/146) and its mean change from ``bscl`` (0.445/0.653) matches the
#     reported 12-month change (0.44/0.65) -> 12 months.
#   - ``fscl`` sits strictly between ``dscl`` (6mo) and ``escl`` (12mo) for both
#     groups, so it is a real, unreported wave -- almost certainly the 9-month
#     point at which the paper (Table 2) checked automated antidepressant
#     refill data, not a SCL-90 interview. Nothing in the paper reports SCL-90
#     completer counts, mean change, or response rates at 9 months to check it
#     against, unlike the other four waves, and this is also the extra wave
#     that produced the original "4 vs 3 follow-ups" discrepancy against the
#     paper. Dropped for that reason.

SCL_TO_MONTHS = {
    "bscl": 0,
    "cscl": 3,
    "dscl": 6,
    "escl": 12,
}

_STANDARDISED_COLS = ["Depres_0", "Depres_f2", "Depres_f3", "Depres_f4", "Depres_f5"]

TIME_INDEPENDENT_COLS = ["Group", "Age", "Sex", "LTC_0", "LTCsev_0"]


def load(file_path=RAW_DATASETS_DIR / "18_Katon_2004" / "katon2004.sav"):
    df = pd.read_spss(file_path).convert_dtypes()
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
    return long_df[head + [c for c in long_df.columns if c not in head]].convert_dtypes()
