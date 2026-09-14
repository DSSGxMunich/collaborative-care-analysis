from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

# Simon 2000 = BMJ 2000;320:550-4, telephone monitoring/feedback/care
# management for primary-care patients starting antidepressants. The paper
# reports 613 patients (196 usual care / 221 feedback only / 196 care
# management); this export has 614, one extra in the care-management arm
# (197). ``randgrp`` is dropped because it duplicates ``group`` exactly
# (-1/0/1 against the labelled strings), and ``group`` is self-describing.


def load(file_path=RAW_DATASETS_DIR / "27_Simon_2000" / "simon2000.sav"):
    df = pd.read_spss(file_path)
    # blank/whitespace-only strings are missing, before dtype inference
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)
    df = df.rename(
        columns={
            "id": "patient_id",
        },
        errors="raise",
    )

    df = df.drop(columns="randgrp")

    incomplete = df["patient_id"].isna() | df["group"].isna()
    if incomplete.any():
        logger.warning(f"Dropped {int(incomplete.sum())} rows with missing patient_id or group.")
        df = df.loc[~incomplete]

    duplicated_id = df["patient_id"].duplicated(keep=False)
    if duplicated_id.any():
        logger.warning(f"Dropped {int(duplicated_id.sum())} rows with duplicated patient_id.")
        df = df.loc[~duplicated_id]

    # unpivot df to long format
    # note what is actually recorded: the average of the scores for 20 depression items
    # in the SCL-90 (each item scores from 0 to 4)
    SCL_FOLLOW_UP_MAP = {
        "sclbase": 0,
        "scl3mo": 3,
        "scl6mo": 6,
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
