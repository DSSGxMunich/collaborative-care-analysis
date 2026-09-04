import pandas as pd

from collaborative_care_analysis.utils import map_with_check

# Comorbidity flags are time-independent (from TIME_INDEPENDENT_COLS in load()).
# As in ds_03_Aragones_2019, the raw INDI export stores them checkbox-style --
# 1 if present, blank otherwise, never an explicit 0. Verified against
# Aragones_2012_standardization_demographics.dta (independently coded, explicit
# 0/1): blank counts match the labelled "No" counts exactly for Diabetes (300),
# Respiratory (309) and Cancer (333). CARDIOVASC additionally carries a single
# 2 (one patient), treated as "yes".
#
# Blank therefore means "absent", not "unknown", so it is filled with "no" after
# the mapping rather than being carried as a ``pd.NA`` key inside it: a ``pd.NA``
# dict key only matches on ``string`` dtype and silently yields NA on Int64 /
# float columns, which ``map_with_check`` cannot catch (it drops nulls before
# asserting). Cross-checked: no patient has a flag set while CHRONICCON is blank.
_YES_NO = {1: "yes", 2: "yes"}
_FLAG_COLS = {
    "HYPERT": "has_hypertension",
    "DIABETES": "has_diabetes",
    "RESPIRATORY": "has_respiratory_disease",
    "CARDIOVASC": "has_cardiovascular_disease",
    "CANCER": "has_cancer",
}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    for raw, harmon in _FLAG_COLS.items():
        harmonized_df[harmon] = map_with_check(harmonized_df[raw], _YES_NO).fillna("no")

    chronic = pd.to_numeric(harmonized_df["CHRONICCON"], errors="raise").fillna(0).astype("Int64")
    assert (chronic >= 0).all(), "CHRONICCON has negative values"
    harmonized_df["number_of_chronic_conditions"] = chronic

    # DUSOI (Duke Severity of Illness Checklist) global score -- baseline
    # physical-comorbidity severity.
    harmonized_df["duke_severity_of_illness_score"] = pd.to_numeric(
        harmonized_df["dtotal"], errors="raise"
    )

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_hypertension",
            "has_diabetes",
            "has_respiratory_disease",
            "has_cardiovascular_disease",
            "has_cancer",
            "number_of_chronic_conditions",
            "duke_severity_of_illness_score",
        ]
    ]
