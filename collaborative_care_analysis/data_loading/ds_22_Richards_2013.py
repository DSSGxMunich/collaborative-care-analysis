import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load():
    base_path = RAW_DATASETS_DIR / "22_Richards_2013"

    baseline = pd.read_spss(base_path / "Richards 2013 CLEANED.sav")
    followup_36m = pd.read_spss(base_path / "Richards 2013_36m CLEANEDn.sav")

    # The 36-month follow-up contains a participant identifier that can be
    # linked to the baseline data. The 12-month follow-up has no unique
    # participant identifier and is therefore not included in the merged dataset.

    # The baseline and 36-month identifiers are stored with different data types,
    # so both are normalized to strings before merging.
    baseline["Origpat_id"] = baseline["Origpat_id"].astype("Int64").astype("string")
    followup_36m["ParticipantID"] = followup_36m["ParticipantID"].astype("Int64").astype("string")

    return baseline.merge(
        followup_36m,
        left_on="Origpat_id",
        right_on="ParticipantID",
        how="left",
        validate="one_to_one",
        suffixes=("", "_36m"),
    )
