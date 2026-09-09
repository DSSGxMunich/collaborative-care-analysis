"""Sanity checks on follow_up_months: it should be numeric, non-negative,
within a plausible range for a collaborative-care trial, and baseline should
be encoded consistently across studies.
"""

import pandas as pd
import pytest
from tests.helpers import COLNAME_FOLLOW_UP

from collaborative_care_analysis.config import COLNAME_STUDYID


def test_follow_up_months_is_numeric(enriched_df: pd.DataFrame) -> None:
    if COLNAME_FOLLOW_UP not in enriched_df.columns:
        pytest.skip(f"'{COLNAME_FOLLOW_UP}' column absent.")
    non_numeric = pd.to_numeric(enriched_df[COLNAME_FOLLOW_UP], errors="coerce")
    bad_mask = non_numeric.isna() & enriched_df[COLNAME_FOLLOW_UP].notna()
    assert not bad_mask.any(), (
        f"{bad_mask.sum()} non-numeric '{COLNAME_FOLLOW_UP}' value(s): "
        f"{sorted(enriched_df.loc[bad_mask, COLNAME_FOLLOW_UP].unique())[:10]}"
    )


def test_follow_up_months_not_negative(enriched_df: pd.DataFrame) -> None:
    if COLNAME_FOLLOW_UP not in enriched_df.columns:
        pytest.skip(f"'{COLNAME_FOLLOW_UP}' column absent.")
    values = pd.to_numeric(enriched_df[COLNAME_FOLLOW_UP], errors="coerce").dropna()
    negative = values[values < 0]
    assert negative.empty, (
        f"{len(negative)} negative '{COLNAME_FOLLOW_UP}' value(s): "
        f"{sorted(negative.unique())[:10]}"
    )


def test_baseline_follow_up_represented_consistently(enriched_df: pd.DataFrame) -> None:
    """Every study should use the same value to mean 'baseline' (typically
    0). A study with no '0' row is either missing its baseline visit or
    coding it with a different value (e.g. 1) -- both are harmonization
    bugs worth fixing at the source.
    """
    needed = [COLNAME_STUDYID, COLNAME_FOLLOW_UP]
    if any(c not in enriched_df.columns for c in needed):
        pytest.skip(f"Missing column(s): {needed}")

    min_by_study = enriched_df.groupby(COLNAME_STUDYID)[COLNAME_FOLLOW_UP].min()
    non_zero_baseline = sorted(min_by_study[min_by_study != 0].index)

    assert not non_zero_baseline, (
        f"{len(non_zero_baseline)} study/studies do not have a "
        f"'{COLNAME_FOLLOW_UP}' == 0 row (minimum observed instead): \n"
        f"{min_by_study.loc[non_zero_baseline]}"
    )


def test_follow_up_months_within_reasonable_bound(enriched_df: pd.DataFrame) -> None:
    """Collaborative-care depression trials rarely follow patients beyond a
    few years. A value far beyond that is more likely a unit error (e.g.
    days or weeks mistakenly loaded as months) than a real follow-up point.

    UPPER_BOUND is a sanity ceiling, not a study-design cutoff -- raise it
    if you have a study with a legitimately long follow-up.
    """
    if COLNAME_FOLLOW_UP not in enriched_df.columns:
        pytest.skip(f"'{COLNAME_FOLLOW_UP}' column absent.")
    UPPER_BOUND_MONTHS = 36
    values = pd.to_numeric(enriched_df[COLNAME_FOLLOW_UP], errors="coerce").dropna()
    too_high = values[values > UPPER_BOUND_MONTHS]
    assert too_high.empty, (
        f"{len(too_high)} '{COLNAME_FOLLOW_UP}' value(s) exceed the "
        f"{UPPER_BOUND_MONTHS}-month sanity ceiling: "
        f"{sorted(too_high.unique())[:10]}. Confirm these are real "
        f"follow-up points, not a unit mismatch."
    )
