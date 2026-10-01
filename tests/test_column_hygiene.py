"""Column-level hygiene checks: no duplicate column names, no two
differently-named columns with identical content, no fully-empty columns,
no constant columns.
"""

import pandas as pd


def test_no_duplicate_column_names(enriched_df: pd.DataFrame) -> None:
    names = list(enriched_df.columns)
    dupes = sorted({c for c in names if names.count(c) > 1})
    assert not dupes, f"Duplicate column name(s): {dupes}"


def test_no_duplicate_column_content(enriched_df: pd.DataFrame) -> None:
    """Two differently-named columns with identical content in every row are
    almost always the same variable produced twice by different
    harmonization scripts."""
    seen: dict[tuple, str] = {}
    dupes: list[tuple[str, str]] = []
    for col in enriched_df.columns:
        fingerprint = tuple(enriched_df[col].astype(object).fillna("<NA>").astype(str))
        if fingerprint in seen:
            dupes.append((seen[fingerprint], col))
        else:
            seen[fingerprint] = col

    assert not dupes, f"Column(s) with identical content to an earlier column: {dupes}"


def test_no_fully_empty_columns(enriched_df: pd.DataFrame) -> None:
    empty_cols = [c for c in enriched_df.columns if enriched_df[c].isna().all()]
    assert not empty_cols, (
        f"{len(empty_cols)} fully-empty (all-NaN) column(s): {empty_cols}. "
        f"Likely a harmonization script that writes the column but never "
        f"populates it, or a join that never matched."
    )


def test_no_constant_columns(enriched_df: pd.DataFrame) -> None:
    """A column with exactly one distinct non-null value carries no
    information for analysis and may indicate a hardcoded/default value
    that was supposed to vary."""
    constant_cols = [c for c in enriched_df.columns if enriched_df[c].nunique(dropna=True) == 1]
    details = {c: enriched_df[c].dropna().iloc[0] for c in constant_cols}
    assert not constant_cols, f"Column(s) with only one distinct value: {details}"
