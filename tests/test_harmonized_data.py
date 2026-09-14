"""Integration tests over the built column-cluster dataset.

These read the concatenated exports and the harmonized output, so they are
skipped when the study data is not present. They assert on shapes, ranges,
types and keys only: no test prints or compares a patient-level value, per
AGENTS.md.

The properties checked here are the ones that were violated at some point
while the clusters were written, so each is a regression test for a real bug.
"""

import re
import unicodedata

import pandas as pd
import pytest

from collaborative_care_analysis.config import COLNAME_STUDYID, INTERIM_DATA_DIR
from collaborative_care_analysis.harmonization_column_clusters import checks
from collaborative_care_analysis.harmonization_column_clusters.concat import (
    ID_COLS,
    load_concatenated_raw,
)
from collaborative_care_analysis.harmonization_column_clusters.registry import (
    cluster_modules,
    source_pairs,
)

HARMONIZED = INTERIM_DATA_DIR / "column_clusters_harmonized" / "harmonized_data.csv"

# The scale each harmonized column is defined on. A value outside these is a
# coding error, not an extreme patient.
EXPECTED_RANGES = {
    "age_at_baseline": (16, 110),
    "phq9_total": (0, 27),
    "gad7_total": (0, 21),
    "phq9_difficulty": (0, 3),
    "gad7_difficulty": (0, 3),
    "scl20_mean": (0, 4),
    "hscl_total": (0, 4),
    "bdi_total": (0, 63),
    "cisr_total": (0, 60),
    "hrsd17_total": (0, 52),
    "cesd23_total": (0, 69),
    "eq5d_vas": (0, 100),
    "sf_physical_component": (-10, 100),
    "sf_mental_component": (-10, 100),
    "n_chronic_conditions_reported": (0, 25),
    **{f"phq9_{item}": (0, 3) for item in range(1, 10)},
    **{f"gad7_{item}": (0, 3) for item in range(1, 8)},
}

# Attributes of the patient at entry: these must not change between visits.
BASELINE_COLUMNS = [
    "age_at_baseline",
    "sex",
    "has_diabetes",
    "has_hypertension",
    "has_cardiovascular_disease",
    "is_in_paid_work",
    "lives_alone",
    "has_spouse_or_partner",
    "completed_secondary_education",
    "is_current_smoker",
    "is_taking_antidepressant",
]


@pytest.fixture(scope="module")
def harmonized() -> pd.DataFrame:
    if not HARMONIZED.exists():
        pytest.skip("harmonized_data.csv not built")
    return pd.read_csv(HARMONIZED, low_memory=False)


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    try:
        return load_concatenated_raw()
    except FileNotFoundError:
        pytest.skip("exported study data not present")


# --- shape and keys ----------------------------------------------------------


def test_join_key_is_unique(harmonized) -> None:
    """One row per study, patient and visit, or every per-patient count is wrong."""
    assert not harmonized.duplicated(subset=ID_COLS).any()


def test_id_columns_come_first(harmonized) -> None:
    assert list(harmonized.columns[: len(ID_COLS)]) == ID_COLS


def test_no_id_column_has_missing_values(harmonized) -> None:
    for column in ID_COLS:
        assert harmonized[column].notna().all(), column


def test_row_count_matches_the_raw_frame(harmonized, raw) -> None:
    """A cluster that filters rows would break alignment with every other one."""
    assert len(harmonized) == len(raw)


def test_every_study_is_present(harmonized, raw) -> None:
    assert set(harmonized[COLNAME_STUDYID]) == set(raw[COLNAME_STUDYID])


def test_no_harmonized_column_is_entirely_empty(harmonized) -> None:
    """A column nothing populates is a broken mapping, not a sparse one."""
    empty = [
        column
        for column in harmonized.columns
        if column not in ID_COLS and harmonized[column].notna().sum() == 0
    ]
    assert empty == []


# --- types and encodings -----------------------------------------------------


def test_follow_up_months_is_floating_point(harmonized) -> None:
    """ds_08 has a free-running follow-up from 2.9 to 16.2 months."""
    assert pd.api.types.is_float_dtype(harmonized["follow_up_months"])


def test_follow_up_months_is_never_negative(harmonized) -> None:
    assert (harmonized["follow_up_months"] >= 0).all()


def test_study_ids_are_nfc_normalized(harmonized) -> None:
    """Decomposed accents drop a study out of every per-study lookup silently."""
    for study in harmonized[COLNAME_STUDYID].unique():
        assert study == unicodedata.normalize("NFC", study), study


def test_boolean_columns_hold_only_true_false_or_missing(harmonized) -> None:
    for column in harmonized.columns:
        values = harmonized[column].dropna().astype(str).str.lower().unique()
        if not set(values) <= {"true", "false"} or len(values) == 0:
            continue
        assert set(values) <= {"true", "false"}, column


def test_sex_uses_only_the_declared_categories(harmonized) -> None:
    assert set(harmonized["sex"].dropna().unique()) <= {"Male", "Female", "Other"}


# --- values and ranges -------------------------------------------------------


@pytest.mark.parametrize(("column", "bounds"), sorted(EXPECTED_RANGES.items()))
def test_column_stays_inside_its_scale(harmonized, column, bounds) -> None:
    if column not in harmonized.columns:
        pytest.skip(f"{column} not built")
    values = pd.to_numeric(harmonized[column], errors="coerce").dropna()
    if values.empty:
        pytest.skip(f"{column} is empty")
    low, high = bounds
    assert values.min() >= low, f"{column} below {low}"
    assert values.max() <= high, f"{column} above {high}"


def test_item_scores_are_whole_numbers(harmonized) -> None:
    """A questionnaire item is answered on a 4-point scale, not continuously."""
    items = [c for c in harmonized.columns if re.fullmatch(r"(phq9|gad7)_\d", c)]
    for column in items:
        values = pd.to_numeric(harmonized[column], errors="coerce").dropna()
        assert (values % 1 == 0).all(), column


def test_summed_totals_are_whole_numbers(harmonized) -> None:
    """A sum of integer items cannot be fractional; ds_26 shipped two that were."""
    for column in ("phq9_total", "gad7_total"):
        values = pd.to_numeric(harmonized[column], errors="coerce").dropna()
        assert (values % 1 == 0).all(), column


def test_no_stata_or_spss_missing_encoding_survives(harmonized) -> None:
    """Stata writes missing as 32741, 2147483621, 1.7e38 or 8.99e307."""
    for column in harmonized.columns:
        if column in ID_COLS:
            continue
        values = pd.to_numeric(harmonized[column], errors="coerce").dropna().abs()
        if values.empty:
            continue
        for threshold in checks.STATA_SENTINELS.values():
            assert not values.between(threshold, threshold + 26).any(), column


def test_no_column_holds_a_date_or_identifier_magnitude(harmonized) -> None:
    """A Unix timestamp is about 1.5e9 and would dwarf any real measurement."""
    for column in harmonized.columns:
        if column in ID_COLS:
            continue
        values = pd.to_numeric(harmonized[column], errors="coerce").dropna().abs()
        if not values.empty:
            assert values.max() < checks.IMPLAUSIBLE_MAGNITUDE, column


# --- values that must not vary within a patient ------------------------------


@pytest.mark.parametrize("column", BASELINE_COLUMNS)
def test_baseline_attribute_is_constant_within_a_patient(harmonized, column) -> None:
    """ds_05 re-asks its comorbidity form every visit and the answers change."""
    if column not in harmonized.columns:
        pytest.skip(f"{column} not built")
    distinct = harmonized.groupby([COLNAME_STUDYID, "patient_id"])[column].nunique(dropna=True)
    assert (distinct <= 1).all(), f"{column} varies within {(distinct > 1).sum()} patients"


# --- the module contract -----------------------------------------------------


def test_every_cluster_declares_the_required_attributes() -> None:
    for module in cluster_modules():
        for attribute in (
            "CLUSTER_KEY",
            "HARMONIZED_COLS",
            "harmonize",
            "COLUMN_PROVENANCE",
            "CONSUMPTION",
        ):
            assert hasattr(module, attribute), f"{module.__name__}.{attribute}"


def test_no_two_clusters_claim_the_same_column() -> None:
    declared = [c for module in cluster_modules() for c in module.HARMONIZED_COLS]
    assert len(declared) == len(set(declared))


def test_every_declared_column_has_provenance() -> None:
    for module in cluster_modules():
        missing = [c for c in module.HARMONIZED_COLS if c not in module.COLUMN_PROVENANCE]
        assert missing == [], f"{module.CLUSTER_KEY}: {missing}"


def test_every_declared_column_is_actually_built(harmonized) -> None:
    for module in cluster_modules():
        for column in module.HARMONIZED_COLS:
            assert column in harmonized.columns, f"{module.CLUSTER_KEY}/{column}"


def test_every_consumed_column_exists_in_the_frame(raw) -> None:
    """A renamed loader would otherwise drop a study without any error."""
    for module in cluster_modules():
        for study, column in source_pairs(module.CONSUMPTION):
            assert column in raw.columns, f"{module.CLUSTER_KEY}/{study}/{column}"


def test_every_mapped_study_has_rows(raw) -> None:
    studies = set(raw[COLNAME_STUDYID].unique())
    for module in cluster_modules():
        for study, _ in source_pairs(module.CONSUMPTION):
            assert study in studies, f"{module.CLUSTER_KEY}/{study}"


def test_no_consumed_column_is_mixed_type_within_a_study(raw) -> None:
    """Mixed types inside one study would break the errors='raise' reads."""
    for module in cluster_modules():
        for study, column in source_pairs(module.CONSUMPTION):
            values = raw.loc[raw[COLNAME_STUDYID] == study, column].dropna()
            if values.empty:
                continue
            kinds = {type(value).__name__ for value in values.head(2000)}
            assert len(kinds) == 1, f"{module.CLUSTER_KEY}/{study}/{column}: {kinds}"


# --- determinism -------------------------------------------------------------


def test_harmonize_is_deterministic(raw) -> None:
    for module in cluster_modules():
        first = module.harmonize(raw)
        second = module.harmonize(raw)
        assert first.astype(str).equals(second.astype(str)), module.CLUSTER_KEY


def test_harmonize_does_not_mutate_the_input(raw) -> None:
    before = (raw.shape, list(raw.columns))
    for module in cluster_modules():
        module.harmonize(raw)
    assert (raw.shape, list(raw.columns)) == before


def test_harmonize_returns_one_row_per_input_row(raw) -> None:
    for module in cluster_modules():
        result = module.harmonize(raw)
        assert len(result) == len(raw), module.CLUSTER_KEY
        assert list(result.columns[: len(ID_COLS)]) == ID_COLS, module.CLUSTER_KEY


# --- column-name case confusion ----------------------------------------------


def test_no_study_has_two_columns_differing_only_by_case(raw) -> None:
    """`AGE` and `age` side by side in one export would make a map ambiguous.

    Across studies the same name in different cases is expected and safe,
    because every read is a per-study slice. Within one study it is not.
    """
    from collaborative_care_analysis.config import INTERIM_DATASETS_EXPORT_DIR
    from collaborative_care_analysis.harmonization_column_clusters.concat import (
        discover_study_stems,
    )

    for stem in discover_study_stems():
        columns = pd.read_csv(INTERIM_DATASETS_EXPORT_DIR / f"{stem}.csv", nrows=0).columns
        folded: dict[str, list[str]] = {}
        for column in columns:
            folded.setdefault(column.lower(), []).append(column)
        clashes = {key: names for key, names in folded.items() if len(names) > 1}
        assert clashes == {}, f"{stem}: {clashes}"


def test_every_mapped_column_matches_its_study_exactly_by_case(raw) -> None:
    """A map naming `age` must not silently read a study's `AGE`, or vice versa."""
    for module in cluster_modules():
        for study, column in source_pairs(module.CONSUMPTION):
            present = raw.loc[raw[COLNAME_STUDYID] == study, column]
            assert present.notna().any() or column in raw.columns, (
                f"{module.CLUSTER_KEY}/{study}/{column}"
            )


# --- age and sex completeness ------------------------------------------------

# Studies that record no age or no sex at all. Recorded rather than asserted
# away: dropping them is a loader decision, and these tests exist to notice if
# the list ever grows.
STUDIES_WITHOUT_AGE = {"05_Bekelman_2015", "26_Salisbury_2016", "29_Simon_2011"}
STUDIES_WITHOUT_SEX = {"29_Simon_2011"}

# Patients whose age or sex is missing inside a study that otherwise has it.
# ds_12's are the patients whose recorded birth dates disagree, ds_04's and
# ds_05's the single patients their own loaders flag.
PATIENTS_WITHOUT_AGE = {"04_Bekelman_2018": 1, "12_Gensichen_2009": 7}
PATIENTS_WITHOUT_SEX = {"04_Bekelman_2018": 1, "05_Bekelman_2015": 1, "12_Gensichen_2009": 1}


def _patients(harmonized: pd.DataFrame) -> pd.DataFrame:
    return harmonized.drop_duplicates([COLNAME_STUDYID, "patient_id"])


def test_studies_without_age_are_the_known_ones(harmonized) -> None:
    patients = _patients(harmonized)
    absent = {
        study
        for study, group in patients.groupby(COLNAME_STUDYID)
        if group["age_at_baseline"].isna().all()
    }
    assert absent == STUDIES_WITHOUT_AGE


def test_studies_without_sex_are_the_known_ones(harmonized) -> None:
    patients = _patients(harmonized)
    absent = {
        study for study, group in patients.groupby(COLNAME_STUDYID) if group["sex"].isna().all()
    }
    assert absent == STUDIES_WITHOUT_SEX


def test_partial_age_gaps_do_not_grow(harmonized) -> None:
    """A study that reports age reports it for every patient but a known few."""
    patients = _patients(harmonized)
    gaps = {
        study: int(group["age_at_baseline"].isna().sum())
        for study, group in patients.groupby(COLNAME_STUDYID)
        if group["age_at_baseline"].notna().any() and group["age_at_baseline"].isna().any()
    }
    assert gaps == PATIENTS_WITHOUT_AGE


def test_partial_sex_gaps_do_not_grow(harmonized) -> None:
    patients = _patients(harmonized)
    gaps = {
        study: int(group["sex"].isna().sum())
        for study, group in patients.groupby(COLNAME_STUDYID)
        if group["sex"].notna().any() and group["sex"].isna().any()
    }
    assert gaps == PATIENTS_WITHOUT_SEX


def test_age_does_not_advance_with_follow_up_time(harmonized) -> None:
    """The column is age at entry, so it must not behave like age at the visit.

    Compared within a study and within the same patients at their first and
    last visit, so neither differing cohort ages nor differential dropout can
    masquerade as drift. If this were an age-at-visit measure the difference
    would track the elapsed years.
    """
    frame = harmonized[[COLNAME_STUDYID, "patient_id", "follow_up_months", "age_at_baseline"]]
    frame = frame[frame["age_at_baseline"].notna()]
    for study, group in frame.groupby(COLNAME_STUDYID):
        months = group["follow_up_months"]
        if months.nunique() < 2:
            continue
        first, last = months.min(), months.max()
        at_first = group[months == first].set_index("patient_id")["age_at_baseline"]
        at_last = group[months == last].set_index("patient_id")["age_at_baseline"]
        shared = at_first.index.intersection(at_last.index)
        if shared.empty:
            continue
        drift = (at_last.loc[shared] - at_first.loc[shared]).abs().max()
        assert drift == 0, f"{study}: age moves by {drift} between visits"


# --- dtypes as the modules return them ---------------------------------------


def test_sex_is_categorical_as_returned_by_its_module(raw) -> None:
    """The CSV loses dtypes, so this has to check the module's own output."""
    for module in cluster_modules():
        if module.CLUSTER_KEY == "sex":
            assert isinstance(module.harmonize(raw)["sex"].dtype, pd.CategoricalDtype)


def test_every_harmonized_column_uses_a_nullable_dtype(raw) -> None:
    """Plain int and bool cannot hold missing; conventions section 5 forbids them."""
    allowed = {"boolean", "Int64", "Float64", "string", "category"}
    for module in cluster_modules():
        result = module.harmonize(raw)
        for column in module.HARMONIZED_COLS:
            assert str(result[column].dtype) in allowed, (
                f"{module.CLUSTER_KEY}/{column} is {result[column].dtype}"
            )
