from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

# Katon 1999 randomised all 228 patients held here, 114 per arm -- unlike
# ds_14/ds_15, this export is the whole trial, not a depression subgroup.
# ``scscl20`` is the screening SCL-20, which is also what the paper reports as
# the baseline clinical characteristic, so it is month 0.
# ``katon1999.CLEANED.sav`` alongside it is the same 228 patients restated in
# the meta-analysis schema (plus empty padding rows), so it adds no cases.


def load(file_path=RAW_DATASETS_DIR / "16_Katon_1999" / "katon1999.sav"):
    df = pd.read_spss(file_path)
    # treat blank or whitespace-only strings as missing
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)
    df = df.rename(
        columns={
            "id": "patient_id",
        },
        errors="raise",
    )

    incomplete = df["patient_id"].isna() | df["assign"].isna()
    if incomplete.any():
        logger.warning(f"Dropped {int(incomplete.sum())} rows with missing patient_id or assign.")
        df = df.loc[~incomplete]

    duplicated_id = df["patient_id"].duplicated(keep=False)
    if duplicated_id.any():
        logger.warning(f"Dropped {int(duplicated_id.sum())} rows with duplicated patient_id.")
        df = df.loc[~duplicated_id]

    # unpivot df to long format
    # note what is actually recorded: the average of the scores for 20 depression items
    # in the SCL-90 (each item scores from 0 to 4)
    SCL_FOLLOW_UP_MAP = {
        "scscl20": 0,
        "m1scl20": 1,
        "m3scl20": 3,
        "m6scl20": 6,
    }
    value_vars = list(SCL_FOLLOW_UP_MAP.keys())
    id_vars = [col for col in df.columns if col not in value_vars]

    long_df = df.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name="_follow_up_months",
        value_name="scl20_mean",
    )
    long_df["follow_up_months"] = map_with_check(
        long_df["_follow_up_months"],
        SCL_FOLLOW_UP_MAP,
    )
    long_df = long_df.drop(columns=["_follow_up_months"])

    if long_df.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    # sort by ["patient_id", "follow_up_months"] and reorder columns
    long_df = long_df.sort_values(["patient_id", "follow_up_months"]).reset_index(drop=True)
    head = ["patient_id", "follow_up_months"]
    tail = [col for col in long_df.columns if col not in head]
    return long_df[head + tail].convert_dtypes()
