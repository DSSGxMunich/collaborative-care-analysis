from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check

# Katon 2001, the relapse-prevention trial: all 386 randomised patients are
# here. ``grp`` is an unlabelled code -- 1 is the relapse prevention
# intervention (n=194), 2 is usual care (n=192). That direction is confirmed
# three ways: the arm sizes and the 71.9% female figure match the paper's
# Table 1, and grp 1 has both lower SCL-20 scores at every follow-up and
# higher antidepressant adherence, as the paper reports.
#
# Do not take the arm labels from ``katon2001.CLEANED.sav``: joined on patient
# id, all 194 grp-1 patients are labelled "Control" there and all 192 grp-2
# patients "Intervention", i.e. the two arms are swapped relative to the paper.
# The file is otherwise the same 386 patients and is not used here.


def load(file_path=RAW_DATASETS_DIR / "17_Katon_2001" / "katon2001.sav"):
    df = pd.read_spss(file_path)
    # treat blank or whitespace-only strings as missing, before dtype inference
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)
    df = df.rename(
        columns={
            "id": "patient_id",
        },
        errors="raise",
    )

    incomplete = df["patient_id"].isna() | df["grp"].isna()
    if incomplete.any():
        logger.warning(f"Dropped {int(incomplete.sum())} rows with missing patient_id or grp.")
        df = df.loc[~incomplete]

    duplicated_id = df["patient_id"].duplicated(keep=False)
    if duplicated_id.any():
        logger.warning(f"Dropped {int(duplicated_id.sum())} rows with duplicated patient_id.")
        df = df.loc[~duplicated_id]

    # unpivot df to long format
    # note what is actually recorded: the average of the scores for 20 depression items
    # in the SCL-90 (each item scores from 0 to 4)
    SCL_FOLLOW_UP_MAP = {
        "bscl20": 0,
        "dscl20": 3,
        "escl20": 6,
        "fscl20": 9,
        "gscl20": 12,
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
