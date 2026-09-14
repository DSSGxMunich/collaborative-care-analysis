import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # 3-arm trial. Descriptive arm names, aligned with the study-level
    # extra-info sheet (intervention_TelCare / intervention_Psychotherapy).
    #   0 = usual care
    #   1 = telephone care management + telephone psychotherapy
    #   2 = telephone care management alone
    # Per the paper's CONSORT and Table 1: group 1 is n=198 (146 female, age
    # 44.8) and group 2 n=207 (148, 44.9), which is the psychotherapy arm and
    # the care-management arm respectively -- the reverse of what the codes
    # suggest.
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["group"],
        {
            0: "control",
            1: "intervention_Psychotherapy",
            2: "intervention_TelCare",
        },
    )

    return harmonized_df[["STUDY_ID", "patient_id", "study_arm", "follow_up_months"]]
