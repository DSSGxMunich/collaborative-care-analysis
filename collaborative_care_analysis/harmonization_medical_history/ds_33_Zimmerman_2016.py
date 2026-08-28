import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Medical history / comorbidity data for this dataset (Diabetes,
    # Hypertension, Cardiac, Respiratory, Cancer) is entirely absent.
    # This was checked directly against the raw .dta file (0/325
    # populated for all five fields) and confirmed by the data provider
    # for now: these columns are artifacts of the pooled
    # meta-analysis template this file is drawn from, not part of the
    # original SMADS dataset - there is no real data behind them, so
    # they are not harmonized here.
    #
    # The only genuine medical-history-adjacent field available is
    # medication adherence, confirmed by the data provider in the
    # meeting with Hannah to be a simple 0/1 coding (0 = No, 1 = Yes). load() already
    # renames the raw "Medadh_0" column to "medication_adherence" and
    # attaches it only to the baseline row (follow_up_months == 0) -
    # its raw follow-up counterpart, "Medadh_f", is excluded entirely
    # from load()'s output because its exact follow-up timing is
    # unresolved (see load()'s own UNRESOLVED_TIME_COLS note), so no
    # follow-up value is available to harmonize here.
    #
    # Per the data provider: missing values here should stay missing -
    # they should NOT be assigned a category (e.g. not treated as "no").
    assert "medication_adherence" in harmonized_df.columns, (
        "medication_adherence column missing from the export"
    )
    yes_no_map = {0: "no", 1: "yes"}
    harmonized_df["is_adherent_to_medication"] = map_with_check(
        harmonized_df["medication_adherence"], yes_no_map, "medication_adherence"
    )

    # return the harmonized dataset which has only the values we want
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "is_adherent_to_medication",
        ]
    ]
