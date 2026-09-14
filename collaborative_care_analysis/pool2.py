"""Load the POOL2 participant-level multi-study export.

POOL2 is a single wide CSV, one row per patient, pooling participant-level data
from most of the source trials. It is **not** placed under ``data_loading/`` on
purpose: the main pipeline must not treat POOL2 as one more dataset. It is a
side input, used to backfill baseline demographics and potentially enrich the
data.

POOL2 numbers studies with its own ``Trial_ID`` (``StudyNo_POOL``), which
differs from this project's dataset numbering (``StudyNo_OURS``). The mapping
between the two lives in ``dataset_id_conversions.csv``.
"""

from pathlib import Path

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import (
    COLNAME_STUDYID,
    DATASET_ID_CONVERSIONS_CSV,
    POOL2_CSV,
    POOL2_DIR,
    POOL2_ZIP,
    normalize_study_id,
)

DATA_LOADING_DIR = Path(__file__).parent / "data_loading"

COLNAME_PATIENT_ID = "patient_id"

# The ``Female`` column is mostly free-text labels; a handful of rows still
# carry a raw code. Only the two clean labels are trusted; anything else
# (a stray "2.0", blanks) becomes missing.
_SEX_MAPPING = {"Female": "Female", "Male": "Male"}

BASELINE_DEMOGRAPHIC_COLS = ["age", "sex"]


def _require_pool2_csv(csv_path: Path) -> None:
    """Raise with the unzip command if the POOL2 export has not been extracted yet."""
    if csv_path.exists():
        return
    raise FileNotFoundError(
        f"POOL2 export not found at {csv_path}.\n"
        f"It ships as a zip that must be extracted first:\n"
        f"    unzip {POOL2_ZIP} -d {POOL2_DIR}\n"
        f"(the archive holds POOL2_final.csv and POOL2_final_NEU.csv at its root)."
    )


def pool_trial_id_to_study_id(csv_path=DATASET_ID_CONVERSIONS_CSV) -> dict[int, str]:
    """Map a POOL2 ``Trial_ID`` to this project's ``STUDY_ID`` (``17`` -> ``17_Katon_2001``).

    ``dataset_id_conversions.csv`` maps the POOL2 study number (``StudyNo_POOL``)
    to this project's dataset number (``StudyNo_OURS``); only its two numeric
    columns are read, as the study-name columns reached the repo with their
    accents mangled. POOL2 trials with no counterpart here (``StudyNo_OURS``
    blank, or a dataset number with no loader) are absent from the result.
    """
    study_id_by_number: dict[int, str] = {}
    for path in DATA_LOADING_DIR.glob("ds_*.py"):
        # Normalized, like dataset._get_study_id: this builds the same STUDY_ID
        # values POOL2 rows are merged on, so the two must agree byte for byte.
        parts = normalize_study_id(path.stem).split("_")  # ds_17_Katon_2001 -> ["ds", "17", ...]
        if len(parts) >= 3 and parts[1].isdigit():
            study_id_by_number[int(parts[1])] = "_".join(parts[1:])

    conversions = pd.read_csv(csv_path).dropna(subset=["StudyNo_POOL", "StudyNo_OURS"])
    return {
        int(row.StudyNo_POOL): study_id_by_number[int(row.StudyNo_OURS)]
        for row in conversions.itertuples(index=False)
        if int(row.StudyNo_OURS) in study_id_by_number
    }


def load(csv_path=POOL2_CSV, conversions_path=DATASET_ID_CONVERSIONS_CSV) -> pd.DataFrame:
    """Load POOL2 as one row per patient, keyed by ``STUDY_ID`` and ``patient_id``.

    ``Trial_ID`` is converted to ``STUDY_ID``; rows whose trial has no
    counterpart in this project are dropped. ``Original_Patient_ID`` (the study's
    own identifier, which matches this project's ``patient_id``) becomes
    ``patient_id``. ``Age`` and ``Female`` are harmonized to the ``age`` /
    ``sex`` conventions used by the ``harmonization_baseline`` cluster. All other
    POOL2 columns are returned unchanged.
    """
    _require_pool2_csv(csv_path)
    df = pd.read_csv(csv_path, low_memory=False)

    trial_id_to_study_id = pool_trial_id_to_study_id(conversions_path)
    df[COLNAME_STUDYID] = df["Trial_ID"].map(trial_id_to_study_id)

    unmapped_trial_ids = sorted(df.loc[df[COLNAME_STUDYID].isna(), "Trial_ID"].dropna().unique())
    if unmapped_trial_ids:
        dropped = int(df[COLNAME_STUDYID].isna().sum())
        logger.info(
            f"POOL2: dropping {dropped} row(s) from {len(unmapped_trial_ids)} trial(s) "
            f"with no dataset in this project: {[int(t) for t in unmapped_trial_ids]}."
        )
    df = df[df[COLNAME_STUDYID].notna()].copy()

    df[COLNAME_PATIENT_ID] = df["Original_Patient_ID"].astype("string")

    df["age"] = pd.to_numeric(df["Age"], errors="raise")

    female = df["Female"].astype("string")
    uncoded = female.notna() & ~female.isin(_SEX_MAPPING)
    if uncoded.any():
        logger.info(
            f"POOL2: {int(uncoded.sum())} row(s) have an unrecognised 'Female' "
            f"value; treating their sex as missing."
        )
    df["sex"] = female.map(_SEX_MAPPING).astype("string")

    if df.duplicated([COLNAME_STUDYID, COLNAME_PATIENT_ID]).any():
        raise ValueError("POOL2 is not unique on (STUDY_ID, patient_id) after ID conversion.")

    head = [COLNAME_STUDYID, COLNAME_PATIENT_ID, *BASELINE_DEMOGRAPHIC_COLS]
    return df[head + [c for c in df.columns if c not in head]].reset_index(drop=True)


def backfill_baseline_demographics(
    merged_df: pd.DataFrame,
    csv_path=POOL2_CSV,
    conversions_path=DATASET_ID_CONVERSIONS_CSV,
) -> pd.DataFrame:
    """Fill missing ``age`` / ``sex`` in the merged frame from POOL2.

    Only cells that are currently missing are touched, and only where POOL2 has
    a value for that ``(STUDY_ID, patient_id)``. A study whose own
    harmonization already provides complete demographics is left untouched.
    The merged frame is one row per patient-visit; POOL2 demographics are
    time-invariant and broadcast to every visit of a patient.
    """
    required = [COLNAME_STUDYID, COLNAME_PATIENT_ID, *BASELINE_DEMOGRAPHIC_COLS]
    missing = [c for c in required if c not in merged_df.columns]
    if missing:
        raise ValueError(f"Merged frame is missing column(s) {missing}.")

    has_gap = merged_df[BASELINE_DEMOGRAPHIC_COLS].isna().any(axis=1)
    if not has_gap.any():
        logger.info("POOL2 backfill: no missing age/sex in the merged frame; nothing to do.")
        return merged_df

    demographics = load(csv_path, conversions_path)[required]
    studies_with_gaps = sorted(merged_df.loc[has_gap, COLNAME_STUDYID].unique())
    covered = sorted(set(studies_with_gaps) & set(demographics[COLNAME_STUDYID]))
    logger.info(
        f"POOL2 backfill: {len(studies_with_gaps)} study/studies have missing age/sex "
        f"({studies_with_gaps}); POOL2 covers {covered}."
    )

    # Join on patient id as a string on both sides: the merged frame may have
    # read it back as an int or float, while POOL2 ids are free-form strings.
    result = merged_df.copy()
    result["_join_id"] = result[COLNAME_PATIENT_ID].astype("string")
    lookup = demographics.rename(
        columns={COLNAME_PATIENT_ID: "_join_id", "age": "_pool_age", "sex": "_pool_sex"}
    )
    lookup["_join_id"] = lookup["_join_id"].astype("string")
    result = result.merge(
        lookup, on=[COLNAME_STUDYID, "_join_id"], how="left", validate="many_to_one"
    )

    result["age"] = pd.to_numeric(result["age"], errors="raise")
    result["sex"] = result["sex"].astype("object")
    for col, pool_col in (("age", "_pool_age"), ("sex", "_pool_sex")):
        fillable = result[col].isna() & result[pool_col].notna()
        result.loc[fillable, col] = result.loc[fillable, pool_col]
        logger.info(
            f"POOL2 backfill: filled {int(fillable.sum())} '{col}' value(s); "
            f"{int(result[col].isna().sum())} still missing."
        )

    return result.drop(columns=["_join_id", "_pool_age", "_pool_sex"])
