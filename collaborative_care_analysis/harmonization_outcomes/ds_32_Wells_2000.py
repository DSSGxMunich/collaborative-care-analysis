import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]

# Partners in Care measured depression with the CES-D, but the file carries it
# under three different scorings that do NOT share a range. Emitting all of them
# as a single ``cesd_total`` would put values from different scales in one
# column, so they are kept apart -- the same rule HARMONIZATION_CONVENTIONS
# applies to BDI vs BDI-II.
#
#   NWCESD    "NEW CESD SCALE", the 23-item sum. Observed 0-67 (a 23-item 0-3
#             scale tops out at 69) and dichotomised at >= 20 by the study's own
#             DPCESD variable -- not the standard 20-item cutoff of 16. Covers
#             months 0/6/12/18/24/48.       -> cesd23_total
#   CESD      the same 23 symptoms expressed as a 0-100 percentage-of-maximum
#             score ("Sum across 23 depressed symptoms 0-100 scale"), so it is a
#             rescaling of the above rather than an independent measure.
#                                            -> cesd23_percent_of_maximum
#   CESD1820  the standard 20-item CES-D, max 60. Collected at month 18 only,
#             so this is the one wave that is directly comparable with a
#             conventional CES-D from another study.
#                                            -> cesd20_total
#
# There is deliberately no plain ``cesd_total`` for this study: any pooled
# analysis has to pick a scale explicitly.
RENAME_MAP = {
    "NWCESD": "cesd23_total",
    "CESD": "cesd23_percent_of_maximum",
    "CESD20": "cesd20_total",
}

# Observed/definitional bounds, checked here so a re-export that silently swaps
# one scoring for another fails loudly instead of polluting the merged dataset.
_RANGES = {
    "cesd23_total": (0, 69),
    "cesd23_percent_of_maximum": (0, 100),
    "cesd20_total": (0, 60),
}


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Wells 2000 (Partners in Care)."""
    harmonized_df = df.copy()

    for raw, harmon in RENAME_MAP.items():
        values = pd.to_numeric(harmonized_df[raw], errors="raise")
        low, high = _RANGES[harmon]
        out_of_range = values.notna() & ((values < low) | (values > high))
        assert not out_of_range.any(), (
            f"{harmon}: {int(out_of_range.sum())} value(s) outside [{low}, {high}]"
        )
        harmonized_df[harmon] = values

    return harmonized_df[ID_COLS + list(RENAME_MAP.values())]
