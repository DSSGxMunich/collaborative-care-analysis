"""Unit tests for the cluster-harmonization diagnostics.

Synthetic frames only, so these run without the study data and can assert on
behaviour the real data happens not to exercise: a Stata sentinel nobody has
hit, a column that is entirely missing, a study that disappears from the
exports.

Each test names the failure it defends against. Every one of them corresponds
to a mistake actually made while building these clusters.
"""

import pandas as pd
import pytest

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.harmonization_column_clusters import checks


def _text(messages: list[str]) -> str:
    return "".join(messages)


def _quiet(messages: list[str]) -> bool:
    return not any("WARNING" in message for message in messages)


def _frame(values: list, study: str = "01_Study_2000"):
    return pd.DataFrame(
        {
            COLNAME_STUDYID: [study] * len(values),
            "patient_id": list(range(len(values))),
            "follow_up_months": [0] * len(values),
            "value": values,
        }
    )


def _visits(values: list, study: str = "s", patient: int = 1):
    return (
        pd.DataFrame(
            {
                COLNAME_STUDYID: [study] * len(values),
                "patient_id": [patient] * len(values),
                "follow_up_months": list(range(len(values))),
            }
        ),
        pd.Series(values, dtype="boolean"),
    )


# --- missing-value encodings -------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "sentinel"),
    [
        ("int", 32741),
        ("long", 2147483621),
        ("float", 1.7014118346046923e38),
        ("double", 8.98846567431158e307),
    ],
)
def test_stata_sentinel_is_reported(kind, sentinel, captured_logs) -> None:
    """A Stata missing marker read as a number must never pass silently."""
    checks.check_magnitude(pd.Series([1.0, 2.0, sentinel]), "c", "s", "col")
    assert f"Stata {kind} missing-value band" in _text(captured_logs)


def test_sentinel_band_covers_the_lettered_codes(captured_logs) -> None:
    """Stata reserves 27 codes per type: the plain dot and .a through .z."""
    checks.check_magnitude(pd.Series([1.0, 32741 + 26]), "c", "s", "col")
    assert "Stata int missing-value band" in _text(captured_logs)


def test_clinical_values_in_the_byte_band_are_not_reported(captured_logs) -> None:
    """Stata's byte band is 101-127, where real blood pressures live."""
    checks.check_magnitude(pd.Series([110, 120, 127]), "c", "s", "systolic")
    assert _quiet(captured_logs)


def test_value_far_above_a_sentinel_is_not_called_a_sentinel(captured_logs) -> None:
    """A Unix timestamp exceeds the int threshold but is a date, not a marker."""
    checks.check_magnitude(pd.Series([1.554e9]), "c", "s", "withdraw")
    text = _text(captured_logs)
    assert "too large for a clinical measurement" in text
    assert "missing-value band" not in text


def test_ordinary_values_produce_no_warning(captured_logs) -> None:
    checks.check_magnitude(pd.Series([0, 14, 27]), "c", "s", "phq9_total")
    assert _quiet(captured_logs)


def test_all_missing_column_does_not_crash_the_magnitude_check() -> None:
    checks.check_magnitude(pd.Series([None, None], dtype="Float64"), "c", "s", "col")


def test_non_numeric_column_does_not_crash_the_magnitude_check() -> None:
    checks.check_magnitude(pd.Series(["yes", "no"]), "c", "s", "col")


# --- ranges ------------------------------------------------------------------


def test_out_of_range_values_are_nulled_and_reported(captured_logs) -> None:
    """A response coded 9 on a 0-3 item is an encoding, not an answer."""
    result = checks.check_range(pd.Series([0.0, 3.0, 9.0]), (0, 3), "c", "item")
    assert result.isna().sum() == 1
    assert result.notna().sum() == 2
    assert "outside (0, 3)" in _text(captured_logs)


def test_in_range_values_survive_untouched() -> None:
    values = pd.Series([0.0, 1.5, 4.0])
    assert checks.check_range(values, (0, 4), "c", "scl20").equals(values)


def test_range_check_leaves_missing_as_missing() -> None:
    result = checks.check_range(pd.Series([None, 2.0]), (0, 3), "c", "item")
    assert result.isna().sum() == 1


def test_negative_value_below_range_is_caught() -> None:
    """ds_11 shipped negative ages; a lower bound has to bite as well."""
    result = checks.check_range(pd.Series([-9.0, 40.0]), (16, 110), "c", "age")
    assert result.isna().sum() == 1


# --- degenerate results ------------------------------------------------------


def test_all_missing_result_is_reported(captured_logs) -> None:
    checks.check_degenerate(pd.Series([pd.NA] * 50, dtype="boolean"), "c", "col", "s")
    assert "missing for every row" in _text(captured_logs)


def test_single_valued_result_is_reported(captured_logs) -> None:
    """A flag that is never true usually means the mapping matched nothing."""
    checks.check_degenerate(pd.Series([False] * 50, dtype="boolean"), "c", "col", "s")
    assert "takes one value" in _text(captured_logs)


def test_small_single_valued_result_is_tolerated(captured_logs) -> None:
    """A handful of identical answers is not evidence of a broken mapping."""
    checks.check_degenerate(pd.Series([True] * 5, dtype="boolean"), "c", "col", "s")
    assert _quiet(captured_logs)


def test_mixed_result_is_not_reported(captured_logs) -> None:
    checks.check_degenerate(pd.Series([True, False] * 25, dtype="boolean"), "c", "col", "s")
    assert _quiet(captured_logs)


# --- values that must not vary within a patient ------------------------------


def test_baseline_attribute_varying_within_patient_is_reported(captured_logs) -> None:
    """Sex or a diagnosis changing between visits is a data-quality problem."""
    df, values = _visits([True, False])
    checks.check_within_patient_constant(df, values, "c", "has_diabetes")
    assert "varies within 1 patient" in _text(captured_logs)


def test_constant_within_patient_passes_quietly(captured_logs) -> None:
    df, values = _visits([True, True])
    checks.check_within_patient_constant(df, values, "c", "col")
    assert _quiet(captured_logs)


def test_missing_does_not_count_as_a_different_value(captured_logs) -> None:
    """A patient answering once and not again has not changed their answer."""
    df, values = _visits([True, pd.NA])
    checks.check_within_patient_constant(df, values, "c", "col")
    assert _quiet(captured_logs)


def test_same_patient_id_in_two_studies_is_not_a_conflict(captured_logs) -> None:
    """2,475 patient ids are reused across studies; the key is (study, patient)."""
    df = pd.DataFrame(
        {
            COLNAME_STUDYID: ["a", "b"],
            "patient_id": [1, 1],
            "follow_up_months": [0, 0],
        }
    )
    checks.check_within_patient_constant(df, pd.Series([True, False], dtype="boolean"), "c", "col")
    assert _quiet(captured_logs)


# --- missing keys and columns ------------------------------------------------


def test_absent_source_column_raises() -> None:
    """A renamed loader must stop the build, not silently drop a study."""
    with pytest.raises(ValueError, match="absent from the concatenated frame"):
        checks.require_columns(_frame([1, 2]), "01_Study_2000", ["nope"], "cluster")


def test_present_source_columns_do_not_raise() -> None:
    checks.require_columns(_frame([1, 2]), "01_Study_2000", ["value"], "cluster")


def test_study_missing_from_the_frame_raises() -> None:
    """A study id matching no rows means the map and the exports disagree."""
    with pytest.raises(ValueError, match="has no rows"):
        checks.require_rows(_frame([1, 2]), "99_Absent_1999", "cluster")


def test_present_study_returns_its_row_mask() -> None:
    assert checks.require_rows(_frame([1, 2, 3]), "01_Study_2000", "cluster").sum() == 3


# --- mapping loss ------------------------------------------------------------


def test_values_lost_in_mapping_are_reported(captured_logs) -> None:
    checks.report_mapping(
        "c", "s", "col", pd.Series([1, 2, 7]), pd.Series([True, False, None], dtype="boolean")
    )
    assert "did not map" in _text(captured_logs)


def test_fully_mapped_column_is_quiet(captured_logs) -> None:
    checks.report_mapping(
        "c", "s", "col", pd.Series([1, 0]), pd.Series([True, False], dtype="boolean")
    )
    assert _quiet(captured_logs)


def test_empty_source_column_is_reported(captured_logs) -> None:
    checks.report_mapping(
        "c",
        "s",
        "col",
        pd.Series([None, None], dtype="Float64"),
        pd.Series([pd.NA, pd.NA], dtype="boolean"),
    )
    assert "entirely empty" in _text(captured_logs)


def test_derived_column_wider_than_its_source_is_quiet(captured_logs) -> None:
    """A value derived from a roster covers rows the named source does not."""
    checks.report_mapping(
        "c",
        "s",
        "col",
        pd.Series([1, None], dtype="Float64"),
        pd.Series([True, False], dtype="boolean"),
    )
    assert _quiet(captured_logs)
