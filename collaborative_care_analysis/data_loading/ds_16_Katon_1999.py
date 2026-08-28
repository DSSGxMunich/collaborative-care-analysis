import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

"""
katon1999.CLEANED.sav has 599 rows, but only the first 228 contain real data.
The remaining 371 rows are entirely blank.
These are dropped before reshaping.

Time-varying columns:
    Depres_0   -> follow_up_months = 0
    Depres_f1  -> follow_up_months = 1
    Depres_f2  -> follow_up_months = 3
    Depres_f3  -> follow_up_months = 6
  all collapsed into a single 'depression_severity' column.

All other columns are broadcast across each patient's follow-up.
"""

DEPRES_MONTH_MAP = {
    "Depres_0": 0.0,
    "Depres_f1": 1.0,
    "Depres_f2": 3.0,
    "Depres_f3": 6.0,
}


def load(file_path=RAW_DATASETS_DIR / "16_Katon_1999" / "katon1999.CLEANED.sav"):
    df = pd.read_spss(file_path)

    # Drop rows with Origpat_id empty or NaN
    df = df[df["Origpat_id"].notna() & (df["Origpat_id"].astype(str).str.strip() != "")]

    missing = [c for c in DEPRES_MONTH_MAP if c not in df.columns]
    if missing:
        raise ValueError(f"Expected columns missing from source file: {missing}")

    value_vars = list(DEPRES_MONTH_MAP.keys())
    id_vars = [c for c in df.columns if c not in value_vars]

    long_df = df.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name="_wave",
        value_name="depression_severity",
    )

    long_df["follow_up_months"] = map_with_check(long_df["_wave"], DEPRES_MONTH_MAP, "_wave")
    long_df = long_df.drop(columns="_wave", errors="raise")

    long_df = long_df.rename(columns={"Origpat_id": "patient_id"}, errors="raise")

    long_df = long_df.sort_values(["patient_id", "follow_up_months"]).reset_index(drop=True)

    front = ["patient_id", "follow_up_months"]
    rest = [c for c in long_df.columns if c not in front]
    long_df = long_df[front + rest]

    long_df = long_df.convert_dtypes()

    return long_df
