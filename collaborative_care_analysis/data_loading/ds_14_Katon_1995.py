from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

# Katon 1995 randomised 217 patients, 91 with major and 126 with minor
# depression. This export holds only the 91 major-depression patients (49
# collaborative care / 42 usual care, matching the paper's Table 2); the minor
# depression arm is not in the data we were given. ``katon1995.CLEANED.sav``
# alongside it is the same 91 patients restated in the meta-analysis schema
# (plus empty padding rows), so it adds no cases and is not used here.


def load(file_path=RAW_DATASETS_DIR / "14_Katon_1995" / "katon1995.sav"):
    df = pd.read_spss(file_path)
    # treat blank or whitespace-only strings as missing
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)
    df = df.rename(
        columns={
            "studyno": "patient_id",
        },
        errors="raise",
    )

    incomplete = df["patient_id"].isna() | df["randgrp"].isna()
    if incomplete.any():
        logger.warning(f"Dropped {int(incomplete.sum())} rows with missing patient_id or randgrp.")
        df = df.loc[~incomplete]

    duplicated_id = df["patient_id"].duplicated(keep=False)
    if duplicated_id.any():
        logger.warning(f"Dropped {int(duplicated_id.sum())} rows with duplicated patient_id.")
        df = df.loc[~duplicated_id]

    # unpivot df to long format
    # note what is actually recorded: the average of the scores for 20 depression items
    # in the SCL-90 (each item scores from 0 to 4)
    SCL_FOLLOW_UP_MAP = {
        "bqscl": 0,
        "f1scl": 1,
        "f4scl": 4,
        "f7scl": 7,
    }

    value_vars = list(SCL_FOLLOW_UP_MAP.keys())
    id_vars = [col for col in df.columns if col not in value_vars]

    long_df = df.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name="_follow_up_months",
        value_name="scl20_mean",
    )

    long_df["follow_up_months"] = map_with_check(long_df["_follow_up_months"], SCL_FOLLOW_UP_MAP)
    long_df = long_df.drop(columns=["_follow_up_months"])

    if long_df.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    # sort by ["patient_id", "follow_up_months"] and reorder columns
    long_df = long_df.sort_values(["patient_id", "follow_up_months"]).reset_index(drop=True)
    head = ["patient_id", "follow_up_months"]
    tail = [col for col in long_df.columns if col not in head]
    return long_df[head + tail].convert_dtypes()
