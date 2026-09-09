"""Depression/anxiety instrument checks: score validity and cross-instrument
coverage for every mood measure in the enriched dataset.
"""

import pandas as pd
import pytest
from tests.helpers import (
    COLNAME_PATIENT_ID,
    DEPRESSION_TOTAL_COLS,
    GAD7_ITEMS,
    PHQ9_ITEMS,
    PHQ9_TOTAL_CANDIDATES,
    assert_in_range,
    find_non_integer_rows,
    present,
)

from collaborative_care_analysis.config import COLNAME_STUDYID

# 1. PHQ-9


def test_phq9_items_in_range(enriched_df: pd.DataFrame) -> None:
    present_items = present(enriched_df, PHQ9_ITEMS)
    if not present_items:
        pytest.skip("No phq9_1..9 item columns present.")
    for col in present_items:
        assert_in_range(enriched_df[col], 0, 3, col)


def test_phq9_total_in_range(enriched_df: pd.DataFrame) -> None:
    if "phq9_total" in enriched_df.columns:
        assert_in_range(enriched_df["phq9_total"], 0, 27, "phq9_total")


def test_phq9_items_and_total_are_integer_valued(enriched_df: pd.DataFrame) -> None:
    """PHQ-9 items (0-3 each) and the total (0-27) are counts and should
    never hold a fractional value like 3.5 -- that usually means an
    averaging/rescaling step ran where a sum should have, or a unit
    conversion was mistakenly applied to a count field.

    Reports study id + patient id for every offending row, so a failure
    points straight at the source data instead of just a column name.
    """
    id_cols = present(enriched_df, [COLNAME_STUDYID, COLNAME_PATIENT_ID])
    cols_to_check = present(enriched_df, PHQ9_ITEMS + PHQ9_TOTAL_CANDIDATES)
    if not cols_to_check:
        pytest.skip("No phq9 item/total columns present.")

    bad_rows = find_non_integer_rows(enriched_df, cols_to_check, id_cols)
    assert bad_rows.empty, (
        f"{len(bad_rows)} non-integer phq9 item/total value(s) found "
        f"(showing up to 20):\n{bad_rows.head(20)}"
    )


def test_phq9_total_matches_item_sum(enriched_df: pd.DataFrame) -> None:
    """Where both the 9 items and a total are present, the total should
    equal the item sum for rows with no missing items."""
    items_present = present(enriched_df, PHQ9_ITEMS)
    if len(items_present) != 9 or "phq9_total" not in enriched_df.columns:
        pytest.skip("Need all 9 phq9 items plus phq9_total to check consistency.")

    complete_rows = (
        enriched_df[items_present].notna().all(axis=1) & enriched_df["phq9_total"].notna()
    )
    if not complete_rows.any():
        pytest.skip("No rows with both complete items and a total to compare.")

    computed = enriched_df.loc[complete_rows, items_present].sum(axis=1)
    stated = enriched_df.loc[complete_rows, "phq9_total"]
    mismatch = complete_rows[complete_rows].index[computed.round(0) != stated.round(0)]

    assert len(mismatch) == 0, (
        f"{len(mismatch)} row(s) where phq9_total doesn't match the sum of "
        f"phq9_1..9. Example row indices: {list(mismatch[:5])}"
    )


def test_phq9_items_imply_phq9_total(enriched_df: pd.DataFrame) -> None:
    """A row with all 9 PHQ-9 items answered should also have a PHQ-9 total
    -- a fully-answered PHQ-9 with no total suggests the harmonization/
    scoring step for that study didn't run or was skipped.
    """
    items_present = present(enriched_df, PHQ9_ITEMS)
    totals_present = present(enriched_df, PHQ9_TOTAL_CANDIDATES)

    if len(items_present) != len(PHQ9_ITEMS):
        pytest.skip(
            f"Not all 9 phq9 item columns present (found {items_present}); "
            f"skipping the complete-row check."
        )
    if not totals_present:
        pytest.fail(
            f"All 9 phq9 item columns are present but no total column "
            f"({PHQ9_TOTAL_CANDIDATES}) exists at all."
        )

    has_all_items = enriched_df[items_present].notna().all(axis=1)
    has_any_total = enriched_df[totals_present].notna().any(axis=1)

    missing_total = has_all_items & ~has_any_total
    assert not missing_total.any(), (
        f"{missing_total.sum()} row(s) have all 9 phq9 items answered but "
        f"no phq9 total in any of {totals_present}."
    )


# 2. Other instrument ranges (GAD-7, K10, HRSD-17, HSCL, CIS-R, PROMIS)


def test_gad7_items_in_range(enriched_df: pd.DataFrame) -> None:
    present_items = present(enriched_df, GAD7_ITEMS)
    if not present_items:
        pytest.skip("No gad7_1..7 item columns present.")
    for col in present_items:
        assert_in_range(enriched_df[col], 0, 3, col)


def test_gad7_total_in_range(enriched_df: pd.DataFrame) -> None:
    if "gad7_total" in enriched_df.columns:
        assert_in_range(enriched_df["gad7_total"], 0, 21, "gad7_total")


def test_k10_total_in_range(enriched_df: pd.DataFrame) -> None:
    if "k10_total" in enriched_df.columns:
        assert_in_range(enriched_df["k10_total"], 10, 50, "k10_total")


def test_hrsd17_total_in_range(enriched_df: pd.DataFrame) -> None:
    if "hrsd17_total" in enriched_df.columns:
        assert_in_range(enriched_df["hrsd17_total"], 0, 52, "hrsd17_total")


def test_hrsd17_suicide_item_in_range(enriched_df: pd.DataFrame) -> None:
    """The HRSD-17 suicide item is scored 0-4."""
    if "hrsd17_suicide_item" in enriched_df.columns:
        assert_in_range(enriched_df["hrsd17_suicide_item"], 0, 4, "hrsd17_suicide_item")


def test_hscl_total_in_range(enriched_df: pd.DataFrame) -> None:
    """hscl_total here appears to be a mean-item score (typical HSCL-D scoring
    is a 1-4 average, not a raw sum). Adjust bounds if your codebook defines
    hscl_total as a raw sum instead."""
    if "hscl_total" in enriched_df.columns:
        assert_in_range(enriched_df["hscl_total"], 1, 4, "hscl_total")


def test_cisr_total_in_range(enriched_df: pd.DataFrame) -> None:
    if "cisr_total" in enriched_df.columns:
        assert_in_range(enriched_df["cisr_total"], 0, 57, "cisr_total")


def test_promis_depression_tscore_in_range(enriched_df: pd.DataFrame) -> None:
    if "promis_depression_tscore" in enriched_df.columns:
        assert_in_range(
            enriched_df["promis_depression_tscore"], 15, 100, "promis_depression_tscore"
        )


# 3. Suicidality fields


def test_suicidality_related_columns_are_binary_or_categorical(enriched_df: pd.DataFrame) -> None:
    """These columns should hold a small, closed set of category codes (e.g.
    yes/no or 0/1), not free text or out-of-scale numerics -- a sign that
    harmonization mapped raw source codes incorrectly."""
    cols = present(
        enriched_df,
        ["suicidal_ideation", "suicidal_plan", "suicide_attempt", "hscl_suicidal"],
    )
    if not cols:
        pytest.skip("No suicidality-related columns present.")

    for col in cols:
        n_unique = enriched_df[col].dropna().nunique()
        assert n_unique <= 10, (
            f"{col} has {n_unique} distinct non-null value(s) -- expected a "
            f"small closed set (binary/categorical). Values seen: "
            f"{sorted(enriched_df[col].dropna().unique())[:10]}"
        )


# 4. Cross-instrument


def test_every_row_has_at_least_one_depression_measure(enriched_df: pd.DataFrame) -> None:
    """Every patient-visit row should have a non-null value in at least one
    depression instrument's total score -- otherwise that row contributes
    nothing to any depression-outcome analysis."""
    present_cols = present(enriched_df, DEPRESSION_TOTAL_COLS)
    if not present_cols:
        pytest.skip("No depression total-score columns present.")

    has_any = enriched_df[present_cols].notna().any(axis=1)
    n_missing = (~has_any).sum()
    pct = 100 * n_missing / len(enriched_df)
    assert n_missing == 0, (
        f"{n_missing} row(s) ({pct:.1f}%) have no depression measure at all across {present_cols}."
    )
