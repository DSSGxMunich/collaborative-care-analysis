from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

# Simon 2011 = "Randomized Trial of Depression Follow-Up Care by Online
# Messaging" (J Gen Intern Med). N = 208 primary-care patients starting
# antidepressants, randomised to usual care (102) or to depression care
# management delivered by online messaging through the medical record (106).
#
# Two assessments only: baseline and a single outcome assessment about five
# months after randomisation. The paper puts the average time from
# randomisation to completion at 155 days and reports ~95% completion, which
# matches this file's 197 non-null ``Depres_f3`` values. Its outcome means by
# arm also reproduce: 0.97 (0.72) intervention and 1.15 (0.81) control against
# the published 0.95 (0.71) and 1.17 (0.81).
#
# Depression severity is the SCL depression scale (mean per item, 0-4), per the
# export's own DepresSev_Mes. ``Age`` and ``Sex`` exist as columns but are
# entirely empty here, so they are dropped rather than carried as all-null.

_STUDY_DIR = RAW_DATASETS_DIR / "29_Simon_2011"

# The single follow-up assessment, ~155 days after randomisation.
DEPRES_TO_MONTHS = {"Depres_0": 0, "Depres_f3": 5}

# Recorded only at the follow-up assessment.
_FOLLOW_UP_ONLY = {"Medadh_f3": "medication_adherence"}

TIME_INDEPENDENT_COLS = ["Group"]

# Constant trial-level metadata, and the two all-empty demographic columns.
_DROP_COLUMNS = {
    "TriaI_id",
    "Time",
    "DepresSev_Mes",
    "DepresD_Mes",
    "LTC_Mes",
    "LTC_incl",
    "LTC_inclType",
    "LTC_emp",
    "Medadh_Mes",
    "Satcare_Mes",
    "Compl_Mes",
    "Age",
    "Sex",
}


def load(file_path=_STUDY_DIR / "simon2011.CLEANED.sav") -> pd.DataFrame:
    # categoricals are kept as labels: Group reads "Intervention"/"Control"
    # rather than a bare 0/1 whose direction has to be rediscovered.
    df = pd.read_spss(file_path)
    # blank/whitespace-only strings are missing, before dtype inference
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)
    df = df.convert_dtypes()
    df = df.rename(columns={"Origpat_id": "patient_id"}, errors="raise")

    if present := sorted(_DROP_COLUMNS & set(df.columns)):
        df = df.drop(columns=present)

    incomplete = df["patient_id"].isna() | df["Group"].isna()
    if incomplete.any():
        logger.warning(f"Dropped {int(incomplete.sum())} rows with missing patient_id or Group.")
        df = df.loc[~incomplete]

    duplicated_id = df["patient_id"].duplicated(keep=False)
    if duplicated_id.any():
        logger.warning(f"Dropped {int(duplicated_id.sum())} rows with duplicated patient_id.")
        df = df.loc[~duplicated_id]

    if unaccounted := sorted(
        set(df.columns)
        - {"patient_id", *TIME_INDEPENDENT_COLS, *DEPRES_TO_MONTHS, *_FOLLOW_UP_ONLY}
    ):
        raise ValueError(f"Columns with no recognised role: {unaccounted}")

    id_vars = ["patient_id", *TIME_INDEPENDENT_COLS]
    long_df = df[id_vars + list(DEPRES_TO_MONTHS)].melt(
        id_vars=id_vars,
        value_vars=list(DEPRES_TO_MONTHS),
        var_name="_col",
        value_name="scl20_mean",
    )
    long_df["follow_up_months"] = map_with_check(long_df["_col"], DEPRES_TO_MONTHS)
    long_df = long_df.drop(columns="_col")

    # Attach the follow-up-only measures to their own visit row.
    follow_up_months = DEPRES_TO_MONTHS["Depres_f3"]
    for raw_col, stem in _FOLLOW_UP_ONLY.items():
        values = df.set_index("patient_id")[raw_col]
        at_follow_up = long_df["follow_up_months"] == follow_up_months
        long_df.loc[at_follow_up, stem] = long_df.loc[at_follow_up, "patient_id"].map(values)

    if long_df.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    long_df = long_df.sort_values(["patient_id", "follow_up_months"]).reset_index(drop=True)
    head = ["patient_id", "follow_up_months"]
    return long_df[head + [c for c in long_df.columns if c not in head]].convert_dtypes()
