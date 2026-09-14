"""Step 1 of PROMPT_column_harmonization.md: concatenate raw per-study exports.

Loads every CSV in ``data/interim/exported_datasets/`` (one per study with a
``load()`` function under ``collaborative_care_analysis/data_loading/``),
tags each with a ``STUDY_ID`` derived from its export filename, and stacks
them into one long-format dataframe. This is deliberately *not* run through
any existing ``harmonization_*`` script -- cluster modules in this package
work from the raw, as-exported columns.

``STUDY_ID`` is not present in the raw exports (see "Ground rules" in
PROMPT_column_harmonization.md): it is only added later in the existing
pipeline, derived from the loader script's filename stem via ``dataset.py``'s
``_get_study_id``. The export step is a 1:1 filename copy of the loader
script name (``ds_17_Katon_2001.py`` -> ``ds_17_Katon_2001.csv``), so that
same function is reused here rather than re-derived, to guarantee a row's
STUDY_ID always matches what the existing ``harmonize`` pipeline would assign.
"""

from pathlib import Path

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID, INTERIM_DATASETS_EXPORT_DIR
from collaborative_care_analysis.dataset import _get_study_id

PACKAGE_DIR = Path(__file__).resolve().parents[1]
DATA_LOADING_DIR = PACKAGE_DIR / "data_loading"

# Every cluster module must keep these columns -- they're the join key across
# clusters and the key the final harmonized_data.csv is built on.
ID_COLS = [COLNAME_STUDYID, "patient_id", "follow_up_months"]


def discover_study_stems() -> list[str]:
    """Return every loader's filename stem, sorted, straight from data_loading/.

    Deriving this from disk (rather than hardcoding study IDs) is required by
    PROMPT_column_harmonization.md so a newly added loader is picked up
    automatically by the next run.
    """
    return sorted(
        script_path.stem
        for script_path in DATA_LOADING_DIR.glob("*.py")
        if script_path.name != "__init__.py"
    )


def load_concatenated_raw() -> pd.DataFrame:
    """Load and vertically concatenate every study's raw export.

    Raises if an export is missing for any loader (run
    ``uv run collaborative_care_analysis/dataset.py export`` first) so a
    stale/partial ``exported_datasets/`` directory fails loudly rather than
    silently under-covering some studies.
    """
    study_stems = discover_study_stems()
    missing = [
        stem for stem in study_stems if not (INTERIM_DATASETS_EXPORT_DIR / f"{stem}.csv").exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"Missing exported CSV(s) for {missing}; run "
            "`uv run collaborative_care_analysis/dataset.py export` first."
        )

    frames = []
    for stem in study_stems:
        study_df = pd.read_csv(INTERIM_DATASETS_EXPORT_DIR / f"{stem}.csv", low_memory=False)
        study_df.insert(0, COLNAME_STUDYID, _get_study_id(Path(stem)))
        frames.append(study_df)

    concatenated = pd.concat(frames, ignore_index=True, sort=False)

    if absent := [col for col in ID_COLS if col not in concatenated.columns]:
        raise ValueError(f"Missing required join key column(s): {absent}")

    _report_frame(concatenated, frames, study_stems)
    return concatenated


def _report_frame(
    concatenated: pd.DataFrame, frames: list[pd.DataFrame], study_stems: list[str]
) -> None:
    """Log the shape of the assembled frame and flag structural problems.

    Three things are worth knowing before any cluster runs: how wide each study
    is, whether the join key is actually unique, and which column names are
    shared between studies. That last one is the quiet hazard, because a
    cluster that maps a column for one study will read the same name in another
    study where it may mean something else entirely.
    """
    logger.info(
        f"Concatenated {len(frames)} study export(s): {len(concatenated)} rows, "
        f"{concatenated.shape[1]} columns."
    )
    widths = sorted(
        ((frame.shape[1], stem) for frame, stem in zip(frames, study_stems, strict=True)),
        reverse=True,
    )
    logger.debug("Widest exports: " + ", ".join(f"{stem} ({width})" for width, stem in widths[:5]))

    duplicated = concatenated.duplicated(subset=ID_COLS, keep=False)
    if duplicated.any():
        affected = concatenated.loc[duplicated, COLNAME_STUDYID].value_counts().to_dict()
        logger.warning(
            f"{int(duplicated.sum())} row(s) share a (study, patient, visit) key, so the "
            f"join key is not unique: {affected}. A cluster that aggregates per patient "
            f"will count these rows more than once."
        )

    shared: dict[str, int] = {}
    for frame in frames:
        for column in frame.columns:
            if column in ID_COLS:
                continue
            shared[column] = shared.get(column, 0) + 1
    reused = {c: n for c, n in shared.items() if n > 1}
    if reused:
        worst = sorted(reused.items(), key=lambda kv: -kv[1])[:8]
        logger.info(
            f"{len(reused)} column name(s) appear in more than one study; the most "
            f"shared are {worst}. Cluster modules must map these per study, never "
            f"frame-wide."
        )


def broadcast_within_patient(df: pd.DataFrame, series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Collapse a per-row series to one value per (STUDY_ID, patient_id).

    Several harmonized variables (age, sex, ...) are expected constant within a
    patient, so broadcasting the first non-null value fills follow-up rows for
    studies that only record it at baseline. The paired ``n_distinct`` lets a
    caller tell that apart from a genuine within-patient disagreement
    (``n_distinct > 1``), so a conflict can be set missing rather than resolved
    to an arbitrary "first" value -- see ``age.harmonize()`` / ``sex.harmonize()``.
    """
    grouped = series.groupby([df[COLNAME_STUDYID], df["patient_id"]])
    return grouped.transform("first"), grouped.transform("nunique")
