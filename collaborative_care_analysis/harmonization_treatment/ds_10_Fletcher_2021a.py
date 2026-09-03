import pandas as pd

from collaborative_care_analysis.utils import map_with_check

# NOT EVERY PATIENT IN THIS DATASET WAS RANDOMISED.
#
# The Decision Support Tool sorted patients into three prognostic groups
# (``severity_r``: 1 = minimal/mild, 2 = moderate, 3 = severe). Only the
# minimal/mild and severe groups were randomised; the moderate group received
# usual care without being randomised and is not part of the trial's 1671
# participants (Fletcher 2021a: "1671 of these patients were included and
# randomly assigned to either the intervention group (n=834) or the control
# group"; "Patients in the moderate group were not [randomised]").
#
# ``group_r_scr`` does not encode that. It is 1 for the whole moderate group,
# so a plain 1 -> "control" mapping silently folds 427 never-randomised
# patients into the control arm (837 real controls -> 1264). The randomised
# counts only reproduce the paper once the moderate group is split out:
#
#   severity_r \ group_r_scr    1     2
#   1 minimal/mild            416   414
#   2 moderate                427     0   <- never randomised
#   3 severe                  421   420
#                             ---   ---
#   randomised (1 and 3)      837   834   == the paper's arm sizes
#
# The moderate group is kept in the dataset -- it is a usable usual-care
# comparison cohort -- but under its own arm label so it can never be pooled
# with the randomised controls by accident.
NOT_RANDOMISED_ARM = "usual_care_notrandomized"

_MODERATE_PROGNOSTIC_GROUP = 2


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # ``group_r_scr``: 1 = control (usual care + attention control),
    # 2 = intervention (prognosis-matched care). Present on every wave file.
    study_arm = map_with_check(
        harmonized_df["group_r_scr"],
        {
            1: "control",
            2: "intervention",
        },
    ).astype("string")

    severity = pd.to_numeric(harmonized_df["severity_r"], errors="raise")
    is_not_randomised = severity.eq(_MODERATE_PROGNOSTIC_GROUP)

    # A moderate-group patient coded as "intervention" would mean the prognostic
    # group and the allocation variable disagree, which the override would hide.
    conflicting = is_not_randomised & study_arm.eq("intervention")
    assert not conflicting.any(), (
        f"{int(conflicting.sum())} row(s) in the non-randomised moderate "
        f"prognostic group are coded as intervention"
    )

    harmonized_df["study_arm"] = study_arm.mask(is_not_randomised, NOT_RANDOMISED_ARM)

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "study_arm",
            "follow_up_months",
        ]
    ]
