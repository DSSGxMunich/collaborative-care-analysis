"""Enrich the merged patient-visit frame with study-level annotations.

The merged dataset is one row per patient-visit. The study-level extra-info
sheet describes the collaborative-care model of each study arm (one row per
``study_id`` / ``treatment_id``). :func:`enrich` joins the sheet onto the
merged frame on study id and study arm, so every patient-visit of an arm
carries that arm's characteristics.

The sheet only describes intervention arms. Control arms of the same studies
receive "no" for every treatment characteristic, since by definition they do
not get the collaborative-care components.
"""

from pathlib import Path

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID, STUDY_LEVEL_EXTRA_INFOS_CSV

COLNAME_STUDY_ARM = "study_arm"
CONTROL_STUDY_ARM = "control"

# Every study-level column added by enrich() gets this prefix.
TREATMENT_COL_PREFIX = "treatment_"

# Extra-info columns that map onto the merged frame's join keys.
COLNAME_EXTRA_INFO_STUDYID = "study_id"
COLNAME_EXTRA_INFO_TREATMENT = "treatment_id"

# Sheet columns that are not data and are dropped before the join: bookkeeping
# ("No", "Study ID"), a duplicate of treatment_id ("Treatment Group"), the
# original info by Hannah.
_EXTRA_INFO_DROP_COLS = [
    "No",
    "Study ID",
    "Treatment Group",
    "HANNAH_Study/Row Id",
    "HANNAH_StudyNo",
]

_JOIN_KEYS = [COLNAME_STUDYID, COLNAME_STUDY_ARM]


def load_study_level_extra_infos(csv_path: Path = STUDY_LEVEL_EXTRA_INFOS_CSV) -> pd.DataFrame:
    """Load the study-level extra-info sheet.

    The sheet carries three header rows -- a category grouping, a
    human-readable label, and the machine column names -- so only the third
    row is used as the header. Non-data columns (see ``_EXTRA_INFO_DROP_COLS``)
    are dropped later, in :func:`enrich`.
    """
    df = pd.read_csv(csv_path, header=2)
    df.columns = [str(c).strip() for c in df.columns]
    logger.info(f"Loaded {len(df)} study-level extra-info row(s), {df.shape[1]} column(s).")
    return df


def enrich(merged_df: pd.DataFrame) -> pd.DataFrame:
    """Merge the study-level extra-info sheet onto the merged patient-visit frame.

    The join is on ``(STUDY_ID, study_arm)`` <-> ``(study_id, treatment_id)``.
    Every patient-visit of a study arm receives that arm's columns. Control
    arms of studies that are in the sheet get "no" for every characteristic;
    arms of studies absent from the sheet keep NaN.
    """
    extra_infos = load_study_level_extra_infos()

    features = extra_infos.drop(
        columns=[c for c in _EXTRA_INFO_DROP_COLS if c in extra_infos.columns]
    ).rename(
        columns={
            COLNAME_EXTRA_INFO_STUDYID: COLNAME_STUDYID,
            COLNAME_EXTRA_INFO_TREATMENT: COLNAME_STUDY_ARM,
        }
    )
    # Namespace the study-level characteristics so they are recognisable in the
    # merged frame and cannot collide with existing columns.
    features = features.rename(
        columns={c: f"{TREATMENT_COL_PREFIX}{c}" for c in features.columns if c not in _JOIN_KEYS}
    )

    missing_keys = [k for k in _JOIN_KEYS if k not in merged_df.columns]
    if missing_keys:
        raise ValueError(f"Merged frame is missing join key(s): {missing_keys}.")

    if features.duplicated(subset=_JOIN_KEYS).any():
        dupes = features.loc[features.duplicated(subset=_JOIN_KEYS, keep=False), _JOIN_KEYS]
        raise ValueError(f"Extra-info sheet is not unique on {_JOIN_KEYS}:\n{dupes}")

    overlap = (set(merged_df.columns) & set(features.columns)) - set(_JOIN_KEYS)
    if overlap:
        raise ValueError(
            f"Extra-info column(s) {sorted(overlap)} already exist in the merged frame."
        )

    unmatched = sorted(set(merged_df[COLNAME_STUDYID].dropna()) - set(features[COLNAME_STUDYID]))
    if unmatched:
        logger.warning(
            f"No study-level extra info for {len(unmatched)} study/studies: {unmatched}."
        )

    before = len(merged_df)
    enriched = merged_df.merge(features, on=_JOIN_KEYS, how="left")
    if len(enriched) != before:
        raise ValueError(f"Enrichment changed the row count from {before} to {len(enriched)}.")

    added = [c for c in features.columns if c not in _JOIN_KEYS]

    # The sheet only describes intervention arms; a control arm of a study that
    # is in the sheet gets "no" everywhere, as it has none of the components.
    in_sheet = enriched[COLNAME_STUDYID].isin(set(features[COLNAME_STUDYID]))
    is_control = in_sheet & enriched[COLNAME_STUDY_ARM].eq(CONTROL_STUDY_ARM)
    enriched.loc[is_control, added] = enriched.loc[is_control, added].fillna("no")
    logger.info(
        f"Enriched merged frame with {len(added)} study-level column(s); "
        f"filled {int(is_control.sum())} control-arm row(s) with 'no'."
    )
    return enriched
