"""Best-effort lookup of a raw column's original meaning, per study.

Used to answer "what did this column actually mean?" when reviewing which raw
columns a harmonized cluster supersedes, and to document value codings when
designing a mapping.

Two sources, in order:

1. ``data/interim/generated_codebooks/<study>/*_metadata.xlsx`` -- the repo's
   own generated codebooks (``uv run python -m collaborative_care_analysis.codebook <id>``),
   whose ``Codebook`` sheet carries ``variable`` / ``variable_label`` /
   ``coded_value`` / ``value_label``. Preferred, since it is the canonical
   artifact and also yields value labels.
2. The study's SPSS/Stata files read directly, for studies whose codebooks have
   not been generated.

Coverage is inherently partial: five studies (ds_03, ds_04, ds_05, ds_24,
ds_25) ship only CSV/Excel data with no embedded metadata, so no codebook can
be generated for them and their columns come back unlabelled. That is reported
honestly rather than filled in with a guess.

Metadata only -- no row of participant data is read.
"""

from functools import cache
from pathlib import Path

from loguru import logger
import pandas as pd
import pyreadstat

from collaborative_care_analysis.codebook import (
    create_variable_labels,
    find_dataset_directory,
    find_statistical_files,
)
from collaborative_care_analysis.config import GENERATED_CODEBOOKS_DIR

NO_LABEL = "(no label in source)"
NO_METADATA = "(source has no embedded metadata)"

# Stata files written by older releases can defeat pyreadstat (it raises
# "Unable to allocate memory" on this repo's PRoMPT exports), so .dta is read
# with pandas, which handles them, and the rest with pyreadstat.
_PYREADSTAT_READERS = {
    ".sav": pyreadstat.read_sav,
    ".zsav": pyreadstat.read_sav,
    ".por": pyreadstat.read_por,
    ".sas7bdat": pyreadstat.read_sas7bdat,
}


def _generated_codebook_files(study_id: str) -> list[Path]:
    study_dir = GENERATED_CODEBOOKS_DIR / study_id
    return sorted(study_dir.glob("*_metadata.xlsx")) if study_dir.is_dir() else []


def _labels_from_generated_codebooks(study_id: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for workbook in _generated_codebook_files(study_id):
        sheet = pd.read_excel(workbook, sheet_name="Codebook")
        for variable, label in zip(sheet["variable"], sheet["variable_label"]):
            if pd.notna(variable) and pd.notna(label) and str(label).strip():
                labels.setdefault(str(variable), str(label).strip())
    return labels


def _labels_from_source_files(study_id: str) -> dict[str, str]:
    numeric_id = int(study_id.split("_")[0])
    try:
        source_files = find_statistical_files(find_dataset_directory(numeric_id))
    except (FileNotFoundError, ValueError) as exc:
        logger.debug(f"{study_id}: no statistical files to read labels from ({exc})")
        return {}

    labels: dict[str, str] = {}
    for file_path in source_files:
        suffix = file_path.suffix.lower()
        try:
            if suffix == ".dta":
                with pd.io.stata.StataReader(file_path) as reader:
                    file_labels = {n: v for n, v in reader.variable_labels().items() if v}
            elif suffix in _PYREADSTAT_READERS:
                _, meta = _PYREADSTAT_READERS[suffix](str(file_path), metadataonly=True)
                labelled = create_variable_labels(meta)  # reuses codebook.py's name/label pairing
                file_labels = dict(
                    zip(labelled["variable"], labelled["variable_label"], strict=True)
                )
                file_labels = {name: label for name, label in file_labels.items() if label}
            else:
                continue
        except Exception as exc:  # noqa: BLE001 - a label is a nice-to-have, never fatal
            logger.debug(f"{study_id}: could not read labels from {file_path.name} ({exc})")
            continue
        for name, label in file_labels.items():
            labels.setdefault(name, label)

    return labels


@cache
def variable_labels_for_study(study_id: str) -> dict[str, str]:
    """Return {raw column name: original variable label} for one study."""
    return _labels_from_generated_codebooks(study_id) or _labels_from_source_files(study_id)


@cache
def value_labels_for_study(study_id: str) -> dict[str, dict]:
    """Return {raw column name: {coded value: value label}} from the generated codebook.

    Empty for studies with no generated codebook. Useful when designing a
    coded -> descriptive mapping for a categorical cluster.
    """
    value_labels: dict[str, dict] = {}
    for workbook in _generated_codebook_files(study_id):
        sheet = pd.read_excel(workbook, sheet_name="Codebook")
        coded = sheet.dropna(subset=["variable", "coded_value", "value_label"])
        for variable, code, label in zip(
            coded["variable"], coded["coded_value"], coded["value_label"]
        ):
            value_labels.setdefault(str(variable), {}).setdefault(code, str(label))
    return value_labels


# Meanings transcribed from a study's *shipped* codebook, for the five studies
# that carry no embedded metadata and so cannot have one generated. Only
# columns actually read out of those documents appear here -- this is a
# transcription, never an inference from the column name.
CURATED_LABELS = {
    # data/raw/Individual Datasets/04_Bekelman_2018/Codebook_Bekelman et al. (2018).xlsx,
    # sheet "CASADescribe".
    ("04_Bekelman_2018", "age"): "Participant age [codebook: derived]",
    ("04_Bekelman_2018", "dem_age"): (
        'age [codebook: demographics; "If pt is >89 years of age, his/her age is recorded as 89"]'
    ),
    # data/raw/Individual Datasets/26_Salisbury_2016/Codebook_.../readme.txt
    ("26_Salisbury_2016", "age_categorical"): (
        "Age band [readme value label 'age_cat': 0=<40, 1=40-49, 2=50-59, 3=60-69, 4=70+]"
    ),
}


def describe_column(study_id: str, column: str) -> str:
    """Return a column's original label, or a marker explaining why there is none."""
    curated = CURATED_LABELS.get((study_id, column))
    if curated:
        return curated

    labels = variable_labels_for_study(study_id)
    if not labels:
        return NO_METADATA
    if column in labels:
        return labels[column]
    # Loaders may lowercase or de-suffix names, so fall back to a case-insensitive match.
    lowered = {name.lower(): label for name, label in labels.items()}
    return lowered.get(column.lower(), NO_LABEL)
