import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.utils import map_with_check

# We take item-level scores and calculate aggregates for common primary outcomes.
# For secondary outcomes we only take sum or mean values

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

PHQ9_COLS = [f"phq{i}" for i in range(1, 10)]

ESSI_COLS = [f"enrichd{i}" for i in range(1, 6)]

GAD7_COLS = [f"gad{i}" for i in range(1, 8)]

HEIQ_COLS = [
    "mheiqtot",  # Mean HEIQ at baseline
    "mfheiqtot",  # Mean HEIQ at follow-up
    "theiqtot",  # Total HEIQ at baseline
    "tfheiqtot",  # Total HEIQ at follow-up
]

SDS_COLS = [
    "msds",
    "mfsds",
    "sdstot",
    "sdsftot",
]

SEQ_COLS = [
    "mseqtot",
    "mfseqtot",
    "tseqtot",
    "tfseqtot",
]

GAD8_MAPPING = {
    "Not at all": 0.0,
    "A little bit": 1.0,
    "Moderately": 2.0,
    "Quite a bit": 3.0,
    "Extremely": 4.0,
    # Allow already-harmonized numeric values
    0.0: 0.0,
    1.0: 1.0,
    2.0: 2.0,
    3.0: 3.0,
    4.0: 4.0,
}

RENAME_MAP = {
    # PHQ-9 items
    **{f"phq{i}": f"phq9_{i}" for i in range(1, 10)},
    # PHQ-9 derived measures
    "phqchange": "phq9_change",  # PHQ at baseine - PHQ at follow-up
    "phqcsc": "phq9_sig_change",
    # SCL-13 items
    **{f"scl{i}": f"scl13_{i}" for i in range(1, 14)},
    # GAD-7 items
    **{f"gad{i}": f"gad7_{i}" for i in range(1, 8)},
    "gad8": "gad7_difficulty",
    # WHO quality of life
    "whoqol1": "whoqol_bref_overall_qol",
    "whoqol2": "whoqol_bref_health_satisfaction",
}

OUTCOME_COLS = ID_COLS + list(RENAME_MAP) + ESSI_COLS + HEIQ_COLS + SDS_COLS + SEQ_COLS


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Conventry 2015."""

    harmonized_df = df[OUTCOME_COLS].copy()

    # Calculate PHQ-9 total only when all nine items are available.
    harmonized_df["phq9_total"] = (
        harmonized_df[PHQ9_COLS]
        .apply(pd.to_numeric, errors="raise")
        .sum(
            axis=1,
            min_count=len(PHQ9_COLS),
        )
        .astype("Int64")
    )

    # Calculate GAD-7 total only when all seven items are available.
    harmonized_df["gad7_total"] = (
        harmonized_df[GAD7_COLS]
        .apply(pd.to_numeric, errors="raise")
        .sum(
            axis=1,
            min_count=len(GAD7_COLS),
        )
        .astype("Int64")
    )

    harmonized_df["gad8"] = map_with_check(
        harmonized_df["gad8"],
        GAD8_MAPPING,
        "gad8",
    ).astype("Float64")

    # Calculate ESSI total only when all five items are available.
    harmonized_df["essi_total"] = (
        harmonized_df[ESSI_COLS]
        .apply(pd.to_numeric, errors="raise")
        .sum(
            axis=1,
            min_count=len(ESSI_COLS),
        )
        .astype("Int64")
    )

    # Use baseline heiQ scores at month 0 and follow-up scores otherwise.
    harmonized_df["heiq_mean"] = harmonized_df["mfheiqtot"].where(
        harmonized_df["follow_up_months"].ne(0),
        harmonized_df["mheiqtot"],
    )

    harmonized_df["heiq_total"] = harmonized_df["tfheiqtot"].where(
        harmonized_df["follow_up_months"].ne(0),
        harmonized_df["theiqtot"],
    )

    harmonized_df["sds_mean"] = harmonized_df["mfsds"].where(
        harmonized_df["follow_up_months"].ne(0),
        harmonized_df["msds"],
    )

    harmonized_df["sds_total"] = harmonized_df["sdsftot"].where(
        harmonized_df["follow_up_months"].ne(0),
        harmonized_df["sdstot"],
    )

    harmonized_df["seq_mean"] = harmonized_df["mfseqtot"].where(
        harmonized_df["follow_up_months"].ne(0),
        harmonized_df["mseqtot"],
    )

    harmonized_df["seq_total"] = harmonized_df["tfseqtot"].where(
        harmonized_df["follow_up_months"].ne(0),
        harmonized_df["tseqtot"],
    )

    # Drop item/source columns used only to construct aggregate scores.
    harmonized_df.drop(
        columns=ESSI_COLS + HEIQ_COLS + SDS_COLS + SEQ_COLS,
        inplace=True,
    )

    return harmonized_df.rename(
        columns=RENAME_MAP,
        errors="raise",
    )
