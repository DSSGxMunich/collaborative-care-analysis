import argparse
from pathlib import Path
from typing import Any

from loguru import logger
import pandas as pd
import pyreadstat

from collaborative_care_analysis.config import (
    GENERATED_CODEBOOKS_DIR,
    RAW_DATASETS_DIR,
)


def find_dataset_directory(
    dataset_id: int,
) -> Path:
    """
    Find the directory corresponding to a dataset ID.
    """
    if not RAW_DATASETS_DIR.exists():
        raise FileNotFoundError(f"Raw-dataset directory does not exist: {RAW_DATASETS_DIR}")

    prefix = f"{dataset_id:02d}_"

    matches = sorted(
        path
        for path in RAW_DATASETS_DIR.iterdir()
        if path.is_dir() and path.name.startswith(prefix)
    )

    if not matches:
        raise FileNotFoundError(
            f"No dataset directory beginning with '{prefix}' was found under {RAW_DATASETS_DIR}."
        )

    if len(matches) > 1:
        matched_names = ", ".join(path.name for path in matches)
        raise RuntimeError(f"Multiple directories matched dataset {dataset_id}: {matched_names}")

    return matches[0]


def find_statistical_files(
    dataset_directory: Path,
) -> list[Path]:
    """
    Find SPSS and Stata files, preferring SPSS when the same
    file is available in both formats.
    """
    candidates = sorted(
        file
        for file in dataset_directory.rglob("*")
        if file.is_file() and file.suffix.lower() in {".sav", ".dta"}
    )

    if not candidates:
        raise FileNotFoundError(f"No .sav or .dta files were found under {dataset_directory}.")

    format_priority = {
        ".sav": 0,
        ".dta": 1,
    }

    selected_files: dict[Path, Path] = {}

    for file in candidates:
        relative_stem = file.relative_to(dataset_directory).with_suffix("")

        current_file = selected_files.get(relative_stem)

        if current_file is None:
            selected_files[relative_stem] = file
            continue

        if format_priority[file.suffix.lower()] < format_priority[current_file.suffix.lower()]:
            selected_files[relative_stem] = file

    return sorted(selected_files.values())


def get_output_directory(
    dataset_directory: Path,
) -> Path:
    output_directory = GENERATED_CODEBOOKS_DIR / dataset_directory.name

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return output_directory


def safe_meta_attribute(meta: Any, attribute: str, default=None):
    """
    Safely retrieve an attribute from the pyreadstat metadata object.

    Some metadata fields exist for SPSS files but not Stata files,
    or vice versa.
    """
    value = getattr(meta, attribute, default)

    if value is None:
        return default

    return value


def convert_to_text(value: Any) -> str:
    """
    Convert metadata values, dictionaries, lists, or ranges into
    readable text for Excel.
    """
    if value is None:
        return ""

    if isinstance(value, dict):
        return "; ".join(f"{key}: {item}" for key, item in value.items())

    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(item) for item in value)

    return str(value)


def get_variable_value_labels(meta: Any) -> dict:
    """
    Return value labels organized by variable.

    Preferred pyreadstat structure:
        meta.variable_value_labels

    Fallback:
        meta.variable_to_label + meta.value_labels
    """
    variable_value_labels = safe_meta_attribute(
        meta,
        "variable_value_labels",
        {},
    )

    if variable_value_labels:
        return variable_value_labels

    variable_to_label = safe_meta_attribute(
        meta,
        "variable_to_label",
        {},
    )

    value_labels = safe_meta_attribute(
        meta,
        "value_labels",
        {},
    )

    reconstructed = {}

    for variable, label_set_name in variable_to_label.items():
        reconstructed[variable] = value_labels.get(
            label_set_name,
            {},
        )

    return reconstructed


# -------------------------------------------------------------------
# Metadata output builders
# -------------------------------------------------------------------


def create_variable_labels(
    meta: Any,
) -> pd.DataFrame:
    """
    Create a simple variable-name and variable-label table.
    """
    column_names = safe_meta_attribute(
        meta,
        "column_names",
        [],
    )

    column_labels = safe_meta_attribute(
        meta,
        "column_labels",
        [],
    )

    # Ensure there is one label entry per variable
    if len(column_labels) < len(column_names):
        column_labels = list(column_labels) + [""] * (len(column_names) - len(column_labels))

    return pd.DataFrame(
        {
            "variable": column_names,
            "variable_label": column_labels,
        }
    )


def create_value_labels(
    meta: Any,
) -> pd.DataFrame:
    """
    Create one row for each value-label mapping.

    Example:
        sex | 1 | Male
        sex | 2 | Female
    """
    variable_value_labels = get_variable_value_labels(meta)

    rows = []

    for variable, mappings in variable_value_labels.items():
        if not isinstance(mappings, dict):
            continue

        for coded_value, value_label in mappings.items():
            rows.append(
                {
                    "variable": variable,
                    "coded_value": coded_value,
                    "value_label": value_label,
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "variable",
                "coded_value",
                "value_label",
            ]
        )

    return pd.DataFrame(rows)


def create_codebook(meta: Any) -> pd.DataFrame:
    """
    Combine variable labels and value labels into one codebook table.

    Variables with value labels have one row per coded value. Variables
    without value labels are retained with empty coded-value fields.
    """
    variable_labels = create_variable_labels(meta)
    value_labels = create_value_labels(meta)

    return variable_labels.merge(
        value_labels,
        on="variable",
        how="left",
    )


def extract_file_metadata(
    file: Path,
    output_directory: Path,
) -> None:
    """
    Extract metadata from one SPSS or Stata file.
    """
    workbook_output = output_directory / f"{file.stem}_metadata.xlsx"

    logger.info(f"Processing {file.name}.")

    suffix = file.suffix.lower()

    # Read only metadata without loading participant-level observations.
    if suffix == ".sav":
        _, meta = pyreadstat.read_sav(
            file,
            metadataonly=True,
        )
    elif suffix == ".dta":
        _, meta = pyreadstat.read_dta(
            file,
            metadataonly=True,
        )
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    codebook = create_codebook(meta)

    with pd.ExcelWriter(
        workbook_output,
        engine="openpyxl",
    ) as writer:
        codebook.to_excel(
            writer,
            sheet_name="Codebook",
            index=False,
        )

        worksheet = writer.sheets["Codebook"]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        for column_cells in worksheet.columns:
            max_length = max(
                len(str(cell.value)) if cell.value is not None else 0
                for cell in column_cells
            )
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(
                max_length + 2,
                60,
            )

    logger.info(f"Saved metadata workbook to {workbook_output}.")


def extract_dataset_metadata(
    dataset_id: int,
) -> None:
    """
    Extract metadata from all SPSS and Stata files for one dataset.
    """
    dataset_directory = find_dataset_directory(dataset_id)

    statistical_files = find_statistical_files(dataset_directory)

    output_directory = get_output_directory(dataset_directory)

    logger.info(f"Found {len(statistical_files)} statistical file(s) in {dataset_directory.name}.")

    failed_files = 0

    for file in statistical_files:
        try:
            extract_file_metadata(
                file=file,
                output_directory=output_directory,
            )
        except (
            OSError,
            ValueError,
            pyreadstat.ReadstatError,
        ):
            failed_files += 1
            logger.exception(f"Failed to extract metadata from {file.name}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("Extract codebook metadata from the SPSS and Stata files of one dataset.")
    )

    parser.add_argument(
        "dataset_id",
        type=int,
        help="Numeric dataset ID, for example 13.",
    )

    arguments = parser.parse_args()

    extract_dataset_metadata(
        dataset_id=arguments.dataset_id,
    )


if __name__ == "__main__":
    main()