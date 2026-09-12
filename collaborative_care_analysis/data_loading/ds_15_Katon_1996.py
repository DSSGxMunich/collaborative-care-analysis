from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

# Katon 1996 randomised 153 patients; the paper reports "65 patients with major
# depression and 88 patients with minor depression". This export is the 65
# major-depression patients (31 intervention / 34 usual care); the minor
# depression arm is not in the data we were given.
# ``Katon1996.CLEANEDsav.sav`` alongside it is the same 65 patients restated in
# the meta-analysis schema (plus empty padding rows), so it adds no cases.
# Despite the near-identical shape, this is a different trial from ds_14
# (Katon 1995, 217 randomised) -- it is the follow-on study, delivered by
# psychologists rather than a consulting psychiatrist.


def load(file_path=RAW_DATASETS_DIR / "15_Katon_1996" / "Katon1996.sav"):
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
