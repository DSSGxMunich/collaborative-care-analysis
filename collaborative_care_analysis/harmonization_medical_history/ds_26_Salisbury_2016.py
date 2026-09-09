import pandas as pd

from collaborative_care_analysis.utils import map_with_check

_YES_NO = {0: "no", 1: "yes"}

# Both confirmed against Table 1 (Salisbury et al. 2016, Lancet Psychiatry
# 3:515-25) by allocation group - exact N/denominator matches, not just
# close percentages:
#   - d_2_4_past_depression: usual care 258/276, intervention 269/295 ==
#     paper's "Previously treated for depression" row exactly.
#   - d_4_1_current_antidepressant: usual care 258/288, intervention
#     251/289 == paper's "Taking antidepressants" row exactly.
# Both are re-asked at every wave (_0/_4/_8/_12), so the loader already
# carries them through as repeated per-visit measures rather than
# baseline-only.
#
# Column names reused from existing medical_history clusters for the same
# construct:
#   - has_history_of_depression: matches ds_05_Bekelman_2015's column of the
#     same name (there derived from CRF_DEP), which that file's own comment
#     defines as "a past/ever diagnosis, distinct from ... current screening
#     status" - the same distinction Table 1 draws here (baseline history
#     vs. the PHQ-9 severity score).
#   - medications_antidepressant: matches ds_04_Bekelman_2018's column of the
#     same name (there derived from med_antid, currently unused/commented
#     out in that file's output list) - same construct, current
#     antidepressant use as a yes/no flag.


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df["has_history_of_depression"] = map_with_check(
        harmonized_df["d_2_4_past_depression"], _YES_NO
    )
    harmonized_df["medications_antidepressant"] = map_with_check(
        harmonized_df["d_4_1_current_antidepressant"], _YES_NO
    )

    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_history_of_depression",
            "medications_antidepressant",
        ]
    ]
