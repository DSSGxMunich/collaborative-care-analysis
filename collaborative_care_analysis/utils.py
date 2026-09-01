from pathlib import Path
import zipfile

from loguru import logger
import pandas as pd
import pyreadstat


def ensure_unzipped(zip_path: Path, extract_dir: Path, marker_path: Path) -> None:
    """Extract zip_path into extract_dir if marker_path doesn't already exist.

    Lets data loaders ship raw files as a .zip in the repo while reading them
    as if already extracted, without re-extracting on every load.
    """
    if marker_path.exists():
        return
    logger.info(f"Extracting {zip_path} to {extract_dir} ...")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)


def map_with_check(series: pd.Series, mapping: dict) -> pd.Series:
    """Map a series through a dict, asserting no unmapped (non-null) values exist.

    .map() silently returns NA for any value not present in the mapping, which
    can hide bad/unexpected raw codes. This makes that failure loud instead.
    """
    label = series.name if series.name is not None else "<unnamed series>"
    non_null = series.dropna()
    unmapped = non_null[~non_null.isin(mapping)]
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
