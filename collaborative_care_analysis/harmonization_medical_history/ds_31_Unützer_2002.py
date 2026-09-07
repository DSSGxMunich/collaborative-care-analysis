import pandas as pd

from collaborative_care_analysis.utils import map_with_check

_YES_NO = {0: "no", 1: "yes"}

# Self-reported chronic-condition checklist (time-invariant; from load()'s
# static columns).
CONDITION_MAP = {
    "ARTHRIT": "has_arthritis",
    "BLADDER": "has_bladder_problems",
    "CANCER": "has_cancer",
    "HEART": "has_heart_disease",
    "HEARVIS": "has_hearing_or_visual_impairment",
    "HIGHBP": "has_hypertension",
    "LUNG": "has_lung_disease",
    "NEURO": "has_neurological_disease",
    "STOMACH": "has_stomach_disease",
    "DIAB": "has_diabetes",
}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    for raw, harmon in CONDITION_MAP.items():
        harmonized_df[harmon] = map_with_check(harmonized_df[raw], _YES_NO)

    harmonized_df["number_of_chronic_conditions"] = pd.to_numeric(
        harmonized_df["NUMDIS2"], errors="raise"
    ).astype("Int64")

    return harmonized_df[
        ["STUDY_ID", "patient_id", "follow_up_months"]
        + list(CONDITION_MAP.values())
        + ["number_of_chronic_conditions"]
    ]
