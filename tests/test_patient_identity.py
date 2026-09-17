"""Checks that patient identity is well-formed in the enriched dataset:
patient_id is never missing, (study, patient, follow-up) uniquely identifies
a row, and a patient never appears in more than one study arm.

These guard against the two most likely failure modes of pooling many
studies' patient-visit tables: a harmonization join fanning out one-to-many
instead of staying one-to-one, and arm assignment getting mixed up across a
patient's follow-up visits.
"""

from pathlib import Path

import pandas as pd
import pytest
from tests.helpers import (
    COLNAME_PATIENT_ID,
    PATIENT_VISIT_KEYS,
    import_loader,
    loader_scripts,
)

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.enrichment import COLNAME_STUDY_ARM


def test_patient_id_not_missing(enriched_df: pd.DataFrame) -> None:
    assert COLNAME_PATIENT_ID in enriched_df.columns, f"'{COLNAME_PATIENT_ID}' column absent."
    n_missing = enriched_df[COLNAME_PATIENT_ID].isna().sum()
    assert n_missing == 0, f"{n_missing} row(s) have a missing '{COLNAME_PATIENT_ID}'."


def test_patient_id_rows_are_unique(enriched_df: pd.DataFrame) -> None:
    """(STUDY_ID, patient_id, follow_up_months) must uniquely identify a row.

    A duplicate here means either the same patient-id was loaded twice,
    or a harmonization cluster join fanned out (one-to-many) instead of
    staying one-to-one.
    """
    missing_keys = [k for k in PATIENT_VISIT_KEYS if k not in enriched_df.columns]
    if missing_keys:
        pytest.skip(f"Missing key column(s) for uniqueness check: {missing_keys}")

    dupes = enriched_df.duplicated(subset=PATIENT_VISIT_KEYS, keep=False)
    assert not dupes.any(), (
        f"{dupes.sum()} row(s) share the same {PATIENT_VISIT_KEYS}:\n"
        f"{enriched_df.loc[dupes, PATIENT_VISIT_KEYS].sort_values(PATIENT_VISIT_KEYS).head(20)}"
    )


def test_each_patient_has_exactly_one_study_arm(enriched_df: pd.DataFrame) -> None:
    """A given (STUDY_ID, patient_id) must map to exactly one study_arm
    across all of that patient's follow-up rows -- a patient cannot be in
    both the intervention and control arm of the same study.
    """
    needed = [COLNAME_STUDYID, COLNAME_PATIENT_ID, COLNAME_STUDY_ARM]
    missing = [c for c in needed if c not in enriched_df.columns]
    if missing:
        pytest.skip(f"Missing column(s) for study-arm check: {missing}")

    arm_counts = (
        enriched_df.dropna(subset=[COLNAME_STUDY_ARM])
        .groupby([COLNAME_STUDYID, COLNAME_PATIENT_ID])[COLNAME_STUDY_ARM]
        .nunique()
    )
    multi_arm_patients = arm_counts[arm_counts > 1]

    assert multi_arm_patients.empty, (
        f"{len(multi_arm_patients)} patient(s) assigned to more than one "
        f"study_arm:\n{multi_arm_patients.head(20)}"
    )


COLNAME_SEX = "sex"
COLNAME_AGE = "age"


def test_patient_has_single_sex(enriched_df: pd.DataFrame) -> None:
    """A given (STUDY_ID, patient_id) must report exactly one sex across all
    of that patient's follow-up rows -- sex is a fixed patient-level
    attribute, not something that should vary visit to visit within the
    harmonized data.
    """
    # Known exception: 05_Bekelman_2015/UZ805 has two distinct sex values
    # across their follow-up rows. Investigated and kept as-is (not a
    # harmonization bug) -- excluded here so it doesn't mask a *new*
    # multi-sex patient showing up elsewhere.
    KNOWN_MULTI_SEX_PATIENTS = {("05_Bekelman_2015", "UZ805")}

    needed = [COLNAME_STUDYID, COLNAME_PATIENT_ID, COLNAME_SEX]
    missing = [c for c in needed if c not in enriched_df.columns]
    assert not missing, f"Missing column(s) for sex consistency check: {missing}"

    grouped = enriched_df.dropna(subset=[COLNAME_SEX]).groupby(
        [COLNAME_STUDYID, COLNAME_PATIENT_ID]
    )
    sex_counts = grouped[COLNAME_SEX].nunique()
    multi_sex = sex_counts[sex_counts > 1]
    multi_sex = multi_sex[~multi_sex.index.isin(KNOWN_MULTI_SEX_PATIENTS)]

    assert multi_sex.empty, (
        f"{len(multi_sex)} patient(s) have more than one distinct "
        f"'{COLNAME_SEX}' value across their follow-up rows:\n{multi_sex.head(20)}"
    )


@pytest.mark.parametrize("script_path", loader_scripts(), ids=lambda p: p.stem)
def test_loader_output_has_no_missing_age_or_sex(script_path: Path) -> None:
    """A loader that reports sex/age at all must not leave missing values in
    those columns -- patients missing sex or age should be dropped by the
    loader itself, and a study that doesn't collect sex/age at all should
    drop the columns entirely rather than emit them full of NaN.
    """
    loader = import_loader(script_path)
    df = loader.load()

    missing_counts = {}
    for col in (COLNAME_SEX, COLNAME_AGE):
        if col in df.columns:
            n_missing = df[col].isna().sum()
            if n_missing:
                missing_counts[col] = int(n_missing)

    assert not missing_counts, (
        f"{script_path.stem}: column(s) with missing sex/age value(s) that "
        f"should have been dropped at the loader: {missing_counts}"
    )


def test_sex_and_age_have_valid_types_and_ranges(enriched_df: pd.DataFrame) -> None:
    """sex should be a pandas 'category' dtype with a small closed set of
    values, and age should be numeric within a plausible human age range --
    catches a harmonization step that leaves sex as raw strings/codes, or an
    age value that's actually a birth year, a code, or a unit error.

    Reports STUDY_ID for any offending value, so a failure points at which
    study's harmonization needs fixing, not just that a problem exists.
    """
    if COLNAME_SEX in enriched_df.columns:
        sex_dtype = enriched_df[COLNAME_SEX].dtype
        assert sex_dtype.name == "category", (
            f"'{COLNAME_SEX}' has dtype '{sex_dtype}', expected 'category'."
        )

        valid_sex = enriched_df.dropna(subset=[COLNAME_SEX])
        n_unique_sex = valid_sex[COLNAME_SEX].nunique()
        if n_unique_sex > 3:
            studies_by_value = (
                valid_sex.groupby(COLNAME_SEX)[COLNAME_STUDYID].unique().apply(sorted)
            )
            assert False, (
                f"'{COLNAME_SEX}' has {n_unique_sex} distinct value(s), expected a "
                f"small closed set. Study id(s) contributing each value:\n{studies_by_value}"
            )

    if COLNAME_AGE in enriched_df.columns:
        valid_age = enriched_df.dropna(subset=[COLNAME_AGE])
        out_of_range = valid_age[(valid_age[COLNAME_AGE] < 17) | (valid_age[COLNAME_AGE] > 100)]
        assert out_of_range.empty, (
            f"{len(out_of_range)} '{COLNAME_AGE}' value(s) outside [17, 100], "
            f"from study id(s) {sorted(out_of_range[COLNAME_STUDYID].unique())}: "
            f"{sorted(out_of_range[COLNAME_AGE].unique())[:10]}"
        )
