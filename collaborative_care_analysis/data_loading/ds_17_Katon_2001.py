from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR
from collaborative_care_analysis.utils import map_with_check


def load(file_path=RAW_DATASETS_DIR / "17_Katon_2001" / "katon2001.sav"):
    df = pd.read_spss(file_path).convert_dtypes()
    df = df.rename(
        columns={
            "id": "patient_id",
        },
        errors="raise",
    )

    # drop rows with missing patient_id or grp
    with_missing_info: int = len(df)
    df = df[
        df["patient_id"].notna() & (df["patient_id"] != "") & df["grp"].notna() & (df["grp"] != "")
    ]
    logger.trace(f"Dropped {with_missing_info - len(df)} rows with missing patient_id or grp.")

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
        value_name="avg_scl90",
    )
    long_df["follow_up_months"] = map_with_check(long_df["_follow_up_months"], SCL_FOLLOW_UP_MAP)
    long_df = long_df.drop(columns=["_follow_up_months"])

    if long_df.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    # sort by ["patient_id", "follow_up_months"] and reorder columns
    long_df = long_df.sort_values(["patient_id", "follow_up_months"]).reset_index(drop=True)
    head = ["patient_id", "follow_up_months"]
    tail = [col for col in long_df.columns if col not in head]
    return long_df[head + tail]
