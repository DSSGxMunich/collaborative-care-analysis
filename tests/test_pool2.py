"""Tests for the POOL2 side loader and the baseline-demographic backfill."""

import numpy as np
import pandas as pd
import pytest

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.dataset import DATA_LOADING_DIR, _get_study_id
from collaborative_care_analysis.pool2 import (
    BASELINE_DEMOGRAPHIC_COLS,
    COLNAME_PATIENT_ID,
    backfill_baseline_demographics,
    load,
    load_baseline_demographics,
    pool_trial_id_to_study_id,
)


def _loader_study_ids() -> set[str]:
    return {
        _get_study_id(path)
        for path in DATA_LOADING_DIR.rglob("*.py")
        if path.name != "__init__.py"
    }


def test_trial_id_conversion_targets_real_datasets() -> None:
    """Every converted POOL2 trial id maps to an actual loader's STUDY_ID."""
    study_ids = set(pool_trial_id_to_study_id().values())
    assert study_ids
    assert study_ids <= _loader_study_ids()


def test_load_is_one_row_per_patient_with_harmonized_demographics() -> None:
    pool = load()

    assert not pool.duplicated([COLNAME_STUDYID, COLNAME_PATIENT_ID]).any()
    assert pool[COLNAME_STUDYID].notna().all()
    assert set(pool[COLNAME_STUDYID]) <= _loader_study_ids()

    assert pd.api.types.is_numeric_dtype(pool["age"])
    assert set(pool["sex"].dropna()) <= {"Male", "Female"}


def test_missing_export_raises_with_unzip_instructions(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="unzip"):
        load(csv_path=tmp_path / "POOL2_final.csv")


def test_load_baseline_demographics_is_a_projection() -> None:
    demographics = load_baseline_demographics()
    assert list(demographics.columns) == [
        COLNAME_STUDYID,
        COLNAME_PATIENT_ID,
        *BASELINE_DEMOGRAPHIC_COLS,
    ]


def test_backfill_only_fills_missing_cells() -> None:
    real_study = next(iter(pool_trial_id_to_study_id().values()))
    pool_rows = load_baseline_demographics()
    pool_rows = pool_rows[pool_rows[COLNAME_STUDYID] == real_study].head(3).reset_index(drop=True)
    assert len(pool_rows) == 3

    merged = pd.DataFrame(
        {
            COLNAME_STUDYID: [real_study] * 4 + ["ZZ_not_in_pool"],
            COLNAME_PATIENT_ID: list(pool_rows[COLNAME_PATIENT_ID]) + ["missing_from_pool", "x"],
            "follow_up_months": [0, 0, 0, 0, 0],
            # first row already has its own values and must be left untouched
            "age": [123.0, np.nan, np.nan, np.nan, np.nan],
            "sex": ["Male", None, None, None, None],
        }
    )

    out = backfill_baseline_demographics(merged)

    assert len(out) == len(merged)
    assert list(out.columns) == list(merged.columns)

    # untouched pre-existing value
    assert out.loc[0, "age"] == 123.0
    assert out.loc[0, "sex"] == "Male"

    # filled from POOL2
    assert out.loc[1, "age"] == pool_rows.loc[1, "age"]
    assert out.loc[2, "sex"] == pool_rows.loc[2, "sex"]

    # no POOL2 row -> still missing
    assert pd.isna(out.loc[3, "age"])
    assert pd.isna(out.loc[4, "age"])


def test_backfill_noop_when_nothing_missing() -> None:
    merged = pd.DataFrame(
        {
            COLNAME_STUDYID: ["17_Katon_2001"],
            COLNAME_PATIENT_ID: ["1"],
            "follow_up_months": [0],
            "age": [50.0],
            "sex": ["Female"],
        }
    )
    out = backfill_baseline_demographics(merged)
    pd.testing.assert_frame_equal(out, merged)
