import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

# Simon 2011 = "Randomized trial of depression follow-up care by online
# messaging" (J Gen Intern Med 2011;26:698-704). RCT, N = 208, primary-care
# patients starting antidepressant treatment: a care manager delivering
# structured follow-up via the electronic health record's secure patient
# messaging vs usual care. Depression severity = SCL-20 (mean, 0-4) at baseline
# and ~5 months (per the dataset codebook).
#
# NOTE: Age and Sex are entirely empty in this file, so no baseline
# harmonization is possible.

_STUDY_DIR = RAW_DATASETS_DIR / "29_Simon_2011"

DEPRES_TO_MONTHS = {
    "Depres_0": 0.0,
    "Depres_f3": 5.0,  # codebook: "SCL-20 after 5 Months"
}

TIME_INDEPENDENT_COLS = ["Group"]


def load(file_path=_STUDY_DIR / "simon2011.CLEANED.sav") -> pd.DataFrame:
    df = pd.read_spss(file_path, convert_categoricals=False).convert_dtypes()
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
    return long_df[head + [c for c in long_df.columns if c not in head]]
