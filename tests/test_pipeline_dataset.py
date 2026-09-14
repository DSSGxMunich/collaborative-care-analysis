"""Tests over the merged pipeline output, where trial arms and loader output live.

Separate from the cluster tests because these properties belong to the
existing per-study pipeline rather than to the column clusters. Skipped when
the enriched dataset has not been built.
"""

import pandas as pd
import pytest

from collaborative_care_analysis.config import COLNAME_STUDYID, INTERIM_DATA_DIR

ENRICHED = INTERIM_DATA_DIR / "enriched_dataset" / "enriched_dataset.csv"

# Patients who were enrolled but never randomised, so they legitimately have no
# arm: ds_24's watchful-waiting group and the one ds_04 patient its loader
# flags. Recorded as counts so the test notices if the number ever changes.
PATIENTS_WITHOUT_ARM = {"24_Rollman_2016": 56, "04_Bekelman_2018": 1}


@pytest.fixture(scope="module")
def enriched() -> pd.DataFrame:
    if not ENRICHED.exists():
        pytest.skip("enriched_dataset.csv not built")
    return pd.read_csv(ENRICHED, low_memory=False)


def _patients(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.drop_duplicates([COLNAME_STUDYID, "patient_id"])


def test_each_patient_belongs_to_exactly_one_arm(enriched) -> None:
    """A patient in two arms would be counted twice in any treatment effect."""
    arms = enriched.groupby([COLNAME_STUDYID, "patient_id"])["study_arm"].nunique(dropna=True)
    assert (arms <= 1).all(), f"{int((arms > 1).sum())} patients in more than one arm"


def test_patients_without_an_arm_are_the_known_unrandomised_ones(enriched) -> None:
    patients = _patients(enriched)
    missing = patients[patients["study_arm"].isna()][COLNAME_STUDYID].value_counts().to_dict()
    assert missing == PATIENTS_WITHOUT_ARM


def test_arm_labels_are_descriptive_not_numeric(enriched) -> None:
    """Conventions require descriptive values, not the source's 0/1/2 codes."""
    arms = enriched["study_arm"].dropna().unique()
    assert all(not str(arm).strip().lstrip("-").isdigit() for arm in arms), sorted(arms)


# Arms name a comparison group. The third prefix is ds_24's watchful-waiting
# group, which was enrolled and followed but never randomised, so it is
# neither a control arm nor an intervention.
ARM_PREFIXES = ("control", "intervention", "usual_care")


def test_every_arm_label_names_a_recognised_group(enriched) -> None:
    for arm in enriched["study_arm"].dropna().unique():
        assert str(arm).startswith(ARM_PREFIXES), arm


def test_arm_is_constant_within_a_patient_across_visits(enriched) -> None:
    """Randomisation happens once; an arm that changes mid-trial is an error."""
    for study, group in enriched.groupby(COLNAME_STUDYID):
        arms = group.groupby("patient_id")["study_arm"].nunique(dropna=True)
        assert (arms <= 1).all(), study


def test_join_key_is_unique(enriched) -> None:
    assert not enriched.duplicated(
        subset=[COLNAME_STUDYID, "patient_id", "follow_up_months"]
    ).any()


def test_no_stata_missing_encoding_reaches_the_enriched_dataset(enriched) -> None:
    """The same sentinel scan as the cluster output, over the wider frame."""
    from collaborative_care_analysis.harmonization_column_clusters import checks

    # Identifiers are excluded: a patient id of 32750 is a real id, and seven
    # of them fall inside Stata's int band by coincidence.
    identifiers = {COLNAME_STUDYID, "patient_id", "follow_up_months"}
    for column in enriched.columns:
        if column in identifiers or column.endswith("_id"):
            continue
        values = pd.to_numeric(enriched[column], errors="coerce").dropna().abs()
        if values.empty:
            continue
        for threshold in checks.STATA_SENTINELS.values():
            assert not values.between(threshold, threshold + 26).any(), column
