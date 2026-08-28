import pandas as pd
import pyreadstat


def map_with_check(series: pd.Series, mapping: dict, label: str) -> pd.Series:
    """Map a series through a dict, asserting no unmapped (non-null) values exist.

    .map() silently returns NA for any value not present in the mapping, which
    can hide bad/unexpected raw codes. This makes that failure loud instead.
    """
    unmapped = series.dropna()[~series.dropna().isin(mapping)]
    assert unmapped.empty, f"{label}: unmapped values present: {unmapped.unique()}"
    return series.map(mapping)


def labeled_variables(file_path) -> set[str]:
    """
    Return the set of variable names that have a non-empty variable_label,
    read directly from the .dta file's own metadata -- mirrors
    create_variable_labels()/safe_meta_attribute() from the codebook
    extraction script, so this doesn't depend on a separately generated
    metadata workbook.
    """
    _, meta = pyreadstat.read_dta(file_path, metadataonly=True)

    column_names = meta.column_names or []
    column_labels = meta.column_labels or []
    # one label entry per variable, same padding logic as create_variable_labels()
    if len(column_labels) < len(column_names):
        column_labels = list(column_labels) + [""] * (len(column_names) - len(column_labels))

    return {name for name, label in zip(column_names, column_labels) if label not in (None, "")}
