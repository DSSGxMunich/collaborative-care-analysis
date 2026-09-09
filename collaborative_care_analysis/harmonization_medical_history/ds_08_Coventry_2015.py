import numpy as np
import pandas as pd

from collaborative_care_analysis.utils import map_with_check

# diabetes/chd are stored as "TRUE"/"FALSE" strings, not 0/1. Counts match
# the paper's N=387 exactly (Coventry et al. 2015, BMJ 350:h638).
_YES_NO = {"TRUE": "yes", "FALSE": "no"}

# qofchd/qofchddiab left out: not in the codebook (only diabetes/chd are),
# likely leftover from linking patients to the NHS QOF registers rather
# than a documented variable.
#
# conditionone-four are free text (91-143 distinct values each) - not
# harmonized, would need manual categorisation.


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["has_diabetes"] = map_with_check(harmonized_df["diabetes"], _YES_NO)
    harmonized_df["has_coronary_heart_disease"] = map_with_check(harmonized_df["chd"], _YES_NO)

    # ndiseases/nfdiseases (Bayliss count of other conditions) and
    # nburden/nfburden (Bayliss Disease Burden) are baseline vs. follow-up
    # pairs, but the loader's "f"-prefix matching misses them ("nfdiseases"
    # doesn't start with f), so both get broadcast to every row instead of
    # merged. 512/729 rows have ndiseases != nfdiseases - picking the right
    # one by visit here.
    is_baseline = harmonized_df["follow_up_months"] == 0
    harmonized_df["number_of_additional_conditions"] = pd.to_numeric(
        np.where(is_baseline, harmonized_df["ndiseases"], harmonized_df["nfdiseases"]),
        errors="raise",
    )
    harmonized_df["disease_burden_score"] = pd.to_numeric(
        np.where(is_baseline, harmonized_df["nburden"], harmonized_df["nfburden"]),
        errors="raise",
    )

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_diabetes",
            "has_coronary_heart_disease",
            "number_of_additional_conditions",
            "disease_burden_score",
        ]
    ]
