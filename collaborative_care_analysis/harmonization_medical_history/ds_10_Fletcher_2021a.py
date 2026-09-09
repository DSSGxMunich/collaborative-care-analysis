import pandas as pd

from collaborative_care_analysis.utils import map_with_check

# chronic/ever_depressed/med are only asked in the baseline survey (present
# on the month-0 row only, per the loader) - broadcast to every visit row,
# same pattern as age/sex in harmonization_baseline for this dataset.
_BASELINE_ONLY_COLS = ["chronic", "ever_depressed", "med"]

_YES_NO = {0: "no", 1: "yes"}
# ever_depressed -> has_history_of_depression to match ds_05/ds_24's name
# for the same idea. med covers any mental health medication (anxiolytics,
# mood stabilizers, etc.), not just antidepressants - named
# on_psychiatric_medication rather than ds_26's medications_antidepressant,
# which would overclaim what this field actually asks.


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    for col in _BASELINE_ONLY_COLS:
        harmonized_df[col] = harmonized_df.groupby("patient_id")[col].transform(
            lambda s: s.ffill().bfill()
        )

    harmonized_df["has_long_term_illness"] = map_with_check(harmonized_df["chronic"], _YES_NO)
    harmonized_df["has_history_of_depression"] = map_with_check(
        harmonized_df["ever_depressed"], _YES_NO
    )
    harmonized_df["on_psychiatric_medication"] = map_with_check(harmonized_df["med"], _YES_NO)

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_long_term_illness",
            "has_history_of_depression",
            "on_psychiatric_medication",
        ]
    ]
