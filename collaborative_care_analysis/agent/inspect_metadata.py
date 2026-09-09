"""Quick terminal inspection of an SPSS / Stata / SAS / CSV / Excel file's schema.

For SPSS / Stata / SAS files this prints **metadata only** by default --
variable names, variable labels, value labels, and the row / column counts --
and never reads or prints a single row of participant data, so it is safe to run
against the sensitive raw files (see ``AGENTS.md``). It is the lightweight
companion to
:mod:`collaborative_care_analysis.codebook`, which writes a full metadata
workbook; this module just dumps the same information to stdout for a fast look
while writing a loader.

``--stats`` additionally reads the data and prints per-column **aggregates**,
which ``AGENTS.md`` explicitly permits ("counts, means, quantiles, null-rates,
distributions"). It is the fastest way to catch a scale that does not lie on its
documented range -- a "GAD-7 total" reaching 26, a "CES-D" reaching 67, an item
score of 9 on a 0-3 item -- before it reaches the merged dataset.

To keep that safe, ``--stats`` deliberately never prints a value that could be
one participant's answer verbatim:

* ``min`` / ``max`` / ``mean`` are shown for **numeric columns only**, where
  they are the 0% and 100% quantiles of a scale.
* non-numeric columns (free text, dates, IDs) get counts only -- number
  non-null, number distinct -- never the values themselves.

CSV and Excel files carry no embedded metadata, so the file is always read in
full to recover its schema (the ``--stats`` distinction does not apply). Only
the column names, per-column dtypes and the aggregates above are printed -- no
row is ever written to stdout. The "variable label" column shows the pandas
dtype, and there are no value-label dictionaries.

Usage::

    # by explicit path
    uv run python -m collaborative_care_analysis.agent.inspect_metadata \\
        "data/raw/Individual Datasets/16_Katon_1999/katon1999.sav"

    # by numeric dataset id (all .sav/.dta files for that study)
    uv run python -m collaborative_care_analysis.agent.inspect_metadata 16

    # include value-label dictionaries
    uv run python -m collaborative_care_analysis.agent.inspect_metadata 16 --values

    # only variables whose name or label matches a (case-insensitive) regex
    uv run python -m collaborative_care_analysis.agent.inspect_metadata 16 --grep scl

    # per-column aggregates: non-null / distinct / min / max / mean
    uv run python -m collaborative_care_analysis.agent.inspect_metadata 16 --stats --grep scl

    # CSV / Excel files (explicit path only; label column shows the dtype)
    uv run python -m collaborative_care_analysis.agent.inspect_metadata some_export.csv --stats
"""

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import pandas as pd
import pyreadstat

from collaborative_care_analysis.codebook import (
    find_dataset_directory,
    find_statistical_files,
)

_READERS = {
    ".sav": pyreadstat.read_sav,
    ".zsav": pyreadstat.read_sav,
    ".por": pyreadstat.read_por,
    ".dta": pyreadstat.read_dta,
    ".sas7bdat": pyreadstat.read_sas7bdat,
}

_FRAME_SUFFIXES = {".csv", ".tsv", ".txt", ".xlsx", ".xls", ".xlsm", ".xlsb", ".ods"}

_SUPPORTED_SUFFIXES = sorted(_READERS) + sorted(_FRAME_SUFFIXES)


def _reader_for(file_path: Path):
    """Return the pyreadstat reader for a file extension."""
    suffix = file_path.suffix.lower()
    try:
        return _READERS[suffix]
    except KeyError:
        raise ValueError(
            f"Unsupported file type {suffix!r}; expected one of {_SUPPORTED_SUFFIXES}."
        ) from None


@dataclass
class _FrameMeta:
    """Minimal stand-in for the pyreadstat metadata object for CSV / Excel files.

    CSV and Excel carry no variable labels or value labels, so the "label" for
    each column is its pandas dtype and ``variable_value_labels`` is empty.
    """

    column_names: list[str]
    column_labels: list[str]
    number_rows: int
    number_columns: int
    variable_value_labels: dict = field(default_factory=dict)

    @classmethod
    def from_frame(cls, frame: pd.DataFrame) -> "_FrameMeta":
        names = [str(c) for c in frame.columns]
        return cls(
            column_names=names,
            column_labels=[str(frame[c].dtype) for c in frame.columns],
            number_rows=len(frame),
            number_columns=frame.shape[1],
        )


def _read_frame(file_path: Path) -> pd.DataFrame:
    """Read a CSV / Excel file into a DataFrame (schema recovery needs the data)."""
    suffix = file_path.suffix.lower()
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(file_path)
    if suffix == ".tsv":
        return pd.read_csv(file_path, sep="\t")
    return pd.read_excel(file_path)


def load_file(file_path: Path, *, with_data: bool) -> tuple[pd.DataFrame | None, Any]:
    """Return ``(data, meta)`` for a stats or CSV / Excel file.

    For stats files ``data`` is ``None`` unless ``with_data`` is set. CSV / Excel
    files have no embedded metadata, so the file is always read to recover the
    schema; ``data`` is still only returned when ``with_data`` is set.
    """
    suffix = file_path.suffix.lower()
    if suffix in _READERS:
        if with_data:
            return _READERS[suffix](str(file_path))
        return None, read_metadata(file_path)
    if suffix in _FRAME_SUFFIXES:
        frame = _read_frame(file_path)
        return (frame if with_data else None), _FrameMeta.from_frame(frame)
    raise ValueError(f"Unsupported file type {suffix!r}; expected one of {_SUPPORTED_SUFFIXES}.")


def read_metadata(file_path: Path) -> Any:
    """Return the pyreadstat metadata object for a stats file (no data read)."""
    _, meta = _reader_for(file_path)(str(file_path), metadataonly=True)
    return meta


def _aligned_labels(meta: Any) -> list[tuple[str, str]]:
    names = list(meta.column_names or [])
    labels = list(meta.column_labels or [])
    labels += [""] * (len(names) - len(labels))
    return [(name, label or "") for name, label in zip(names, labels)]


def column_stats(series: pd.Series) -> str:
    """Summarise one column as aggregates only.

    Numeric columns get non-null count, distinct count, min, max and mean --
    order statistics and a mean, never a named participant's record. Everything
    else (free text, dates, identifiers) gets counts only, so no raw value can
    reach stdout. See ``AGENTS.md``.
    """
    n_non_null = int(series.notna().sum())
    n_unique = int(series.nunique(dropna=True))
    summary = f"n={n_non_null} distinct={n_unique}"

    numeric = pd.to_numeric(series, errors="coerce")
    is_numeric = n_non_null > 0 and numeric.notna().sum() == n_non_null
    if not is_numeric:
        return summary

    return f"{summary} min={numeric.min():g} max={numeric.max():g} mean={numeric.mean():.3f}"


def describe_file(
    file_path: Path,
    *,
    show_value_labels: bool = False,
    show_stats: bool = False,
    name_or_label_regex: str | None = None,
) -> None:
    """Print the schema of one stats / CSV / Excel file to stdout.

    For stats files this is metadata only unless ``show_stats`` is set, in which
    case the data is read and each column is summarised by :func:`column_stats`
    (aggregates only). CSV / Excel files are always read to recover the schema;
    ``show_stats`` still controls whether the aggregates are printed.
    """
    pattern = re.compile(name_or_label_regex, re.IGNORECASE) if name_or_label_regex else None

    data, meta = load_file(file_path, with_data=show_stats)

    value_labels = getattr(meta, "variable_value_labels", {}) or {}

    print(f"# {file_path.name}")
    print(f"rows={meta.number_rows} cols={meta.number_columns}")

    for name, label in _aligned_labels(meta):
        if pattern and not (pattern.search(name) or pattern.search(label)):
            continue
        line = f"{name}\t{label}"
        if show_stats and data is not None and name in data.columns:
            line += f"\t:: {column_stats(data[name])}"
        if show_value_labels and name in value_labels:
            line += f"\t:: {value_labels[name]}"
        print(line)


def _resolve_targets(target: str) -> list[Path]:
    """Interpret ``target`` as a file path or a numeric dataset id."""
    path = Path(target)
    if path.exists():
        return [path]
    if target.isdigit():
        return find_statistical_files(find_dataset_directory(int(target)))
    raise FileNotFoundError(f"{target!r} is neither an existing file nor a numeric dataset id.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "target",
        help=(
            "Path to a .sav/.dta/.sas7bdat/.csv/.xlsx file, or a numeric dataset "
            "id (e.g. 16, resolves to that study's .sav/.dta files)."
        ),
    )
    parser.add_argument(
        "--values",
        action="store_true",
        help="Also print the value-label dictionary for each labelled variable.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help=(
            "Read the data and print per-column aggregates (non-null, distinct, and "
            "for numeric columns min/max/mean). Never prints individual values."
        ),
    )
    parser.add_argument(
        "--grep",
        metavar="REGEX",
        default=None,
        help="Only show variables whose name or label matches this regex (case-insensitive).",
    )
    args = parser.parse_args()

    for i, file_path in enumerate(_resolve_targets(args.target)):
        if i:
            print()
        describe_file(
            file_path,
            show_value_labels=args.values,
            show_stats=args.stats,
            name_or_label_regex=args.grep,
        )


if __name__ == "__main__":
    main()
