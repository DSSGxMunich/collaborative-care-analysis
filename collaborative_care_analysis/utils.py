import pandas as pd


def map_with_check(series: pd.Series, mapping: dict, label: str) -> pd.Series:
    """Map a series through a dict, asserting no unmapped (non-null) values exist.

    .map() silently returns NA for any value not present in the mapping, which
    can hide bad/unexpected raw codes. This makes that failure loud instead.
    """
    unmapped = series.dropna()[~series.dropna().isin(mapping)]
    assert unmapped.empty, f"{label}: unmapped values present: {unmapped.unique()}"
    return series.map(mapping)
