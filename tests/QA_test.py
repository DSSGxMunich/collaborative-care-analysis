"""QA test suite for the collaborative-care-analysis pipeline.

Covers, in order:
  1. Study ID consistency between loaders and the extra-info sheet
  2. Loader-level dtype hygiene (parametrized per loader script)
  3. Enriched-file basic integrity (non-empty, join keys, row count)
  4. Patient-level identity and uniqueness
  5. follow_up_months integrity
  6. Study-level enrichment/treatment-column correctness
  7. PHQ-9 item/total consistency
  8. Other depression-instrument range checks (GAD-7, K10, HRSD-17, HSCL,
     CIS-R, PROMIS Depression)
  9. Suicidality-field sanity
  10. Cross-instrument sanity
  11. Column-level hygiene (duplicate names/content, empty, constant columns)
  12. Missingness report (diagnostic only)
"""

import importlib
from pathlib import Path

from loguru import logger
import pandas as pd
import pytest

from collaborative_care_analysis.config import (
    COLNAME_STUDYID,
    ENRICHED_DATASET_DIR,
    MERGED_DATASET_DIR,
)
from collaborative_care_analysis.dataset import DATA_LOADING_DIR, PACKAGE_DIR, _get_study_id
from collaborative_care_analysis.enrichment import (
    COLNAME_EXTRA_INFO_STUDYID,
    COLNAME_STUDY_ARM,
    CONTROL_STUDY_ARM,
    TREATMENT_COL_PREFIX,
    enrich,
    load_study_level_extra_infos,
)

ENRICHED_CSV = ENRICHED_DATASET_DIR / "enriched_dataset.csv"
MERGED_CSV = MERGED_DATASET_DIR / "merged_dataset.csv"

COLNAME_PATIENT_ID = "patient_id"
COLNAME_FOLLOW_UP = "follow_up_months"
PATIENT_VISIT_KEYS = [COLNAME_STUDYID, COLNAME_PATIENT_ID, COLNAME_FOLLOW_UP]

PHQ9_ITEMS = [f"phq9_{i}" for i in range(1, 10)]
PHQ9_TOTAL_CANDIDATES = ["phq9_total"]

GAD7_ITEMS = [f"gad7_{i}" for i in range(1, 8)]

DEPRESSION_TOTAL_COLS = [
    "phq9_total",
    "hrsd17_total",
    "hscl_total",
    "k10_total",
    "cisr_total",
    "promis_depression_tscore",
]


# ==========================================================================
# Fixtures and shared helpers
# ==========================================================================


@pytest.fixture(scope="module")
def merged_df() -> pd.DataFrame:
    if not MERGED_CSV.exists():
        pytest.skip(f"{MERGED_CSV} not found. Run the 'merge' pipeline step first.")
    return pd.read_csv(MERGED_CSV)


@pytest.fixture(scope="module")
def enriched_df() -> pd.DataFrame:
    if not ENRICHED_CSV.exists():
        pytest.skip(f"{ENRICHED_CSV} not found. Run the 'enrich' pipeline step first.")
    return pd.read_csv(ENRICHED_CSV)


@pytest.fixture(scope="module")
def treatment_cols(enriched_df: pd.DataFrame) -> list[str]:
    return [c for c in enriched_df.columns if c.startswith(TREATMENT_COL_PREFIX)]


def _present(df: pd.DataFrame, cols: list[str]) -> list[str]:
    """Return only the columns that actually exist in this dataset."""
    return [c for c in cols if c in df.columns]


def _assert_in_range(series: pd.Series, low: float, high: float, label: str) -> None:
    valid = series.dropna()
    out_of_range = valid[(valid < low) | (valid > high)]
    assert out_of_range.empty, (
        f"{label}: {len(out_of_range)} value(s) outside [{low}, {high}]: "
        f"{sorted(out_of_range.unique())[:10]}"
    )


def _loader_scripts() -> list[Path]:
    return [p for p in sorted(DATA_LOADING_DIR.rglob("*.py")) if p.name != "__init__.py"]


def _import_loader(script_path: Path):
    module_path = ".".join(
        (
            "collaborative_care_analysis",
            *script_path.relative_to(PACKAGE_DIR).with_suffix("").parts,
        )
    )
    return importlib.import_module(module_path)


def _loader_study_ids() -> set[str]:
    """STUDY_ID of every data-loading script (e.g. '16_Katon_1999')."""
    return {
        _get_study_id(path)
        for path in DATA_LOADING_DIR.rglob("*.py")
        if path.name != "__init__.py"
    }


# ==========================================================================
# 1. Study ID consistency between loaders and the extra-info sheet
# ==========================================================================


def test_study_ids_match_between_extra_infos_and_datasets() -> None:
    """The extra-info sheet's study ids line up exactly with the datasets.

    ``enrich`` does an exact join, so any mismatch here has to be fixed by
    correcting the identifier at the source (the sheet or the loader), not
    with fuzzy matching.
    """
    extra_ids = set(load_study_level_extra_infos()[COLNAME_EXTRA_INFO_STUDYID])
    loader_ids = _loader_study_ids()

    missing_from_sheet = loader_ids - extra_ids
    unexpected_in_sheet = extra_ids - loader_ids

    assert not missing_from_sheet and not unexpected_in_sheet, (
        f"study id mismatch between the extra-info sheet and the datasets:\n"
        f"  missing from sheet: {sorted(missing_from_sheet)}\n"
        f"  unexpected in sheet: {sorted(unexpected_in_sheet)}"
    )


# ==========================================================================
# 2. Loader-level dtype hygiene (before anything hits a CSV)
# ==========================================================================


@pytest.mark.parametrize("script_path", _loader_scripts(), ids=lambda p: p.stem)
def test_loader_output_uses_nullable_dtypes(script_path: Path) -> None:
    """Every loader's output must use pandas' nullable dtypes (Int64,
    Float64, boolean, string) rather than plain numpy dtypes.

    Numpy int64/bool cannot represent missing values -- pandas silently
    upcasts a numpy int column with NaN to float64, which is how integer
    codes quietly become '1.0' or how missingness gets masked as 0. Nullable
    dtypes make missingness explicit and force every downstream step to
    handle it deliberately, instead of only surfacing once a CSV round-trip
    already lost the distinction.
    """
    loader = _import_loader(script_path)
    df = loader.load()

    non_nullable = []
    for col in df.columns:
        dtype = df[col].dtype
        is_nullable_ext = pd.api.types.is_extension_array_dtype(dtype)
        is_plain_object = dtype == object  # free-text/string columns are fine as object
        if not (is_nullable_ext or is_plain_object):
            non_nullable.append((col, str(dtype)))

    assert not non_nullable, (
        f"{script_path.stem}: column(s) with a non-nullable dtype leaving the "
        f"loader (use e.g. 'Int64'/'Float64'/'boolean' instead of numpy "
        f"int64/float64/bool): {non_nullable}"
    )


@pytest.mark.parametrize("script_path", _loader_scripts(), ids=lambda p: p.stem)
def test_loader_columns_have_single_inferred_type(script_path: Path) -> None:
    """No column should mix incompatible Python value types (e.g. some rows
    numeric, some rows string) within the same column.

    This is distinct from the nullable-dtype check: an ``object`` column of
    strings is fine, but an ``object`` column mixing ``"3"`` and ``3`` and
    ``True`` is a sign of inconsistent recoding.
    """
    loader = _import_loader(script_path)
    df = loader.load()

    mixed_cols = []
    for col in df.columns:
        inferred = pd.api.types.infer_dtype(df[col], skipna=True)
        if inferred in ("mixed", "mixed-integer"):
            mixed_cols.append(col)

    assert not mixed_cols, (
        f"{script_path.stem}: column(s) with mixed value types: {mixed_cols}. "
        f"Inspect with df['<col>'].apply(type).value_counts()."
    )


# ==========================================================================
# 3. Enriched-file basic integrity
# ==========================================================================


def test_enriched_file_is_not_empty(enriched_df: pd.DataFrame) -> None:
    assert not enriched_df.empty, "enriched_dataset.csv has no rows."


def test_join_keys_present(enriched_df: pd.DataFrame) -> None:
    missing = [k for k in (COLNAME_STUDYID, COLNAME_STUDY_ARM) if k not in enriched_df.columns]
    assert not missing, f"Missing join key column(s): {missing}"


def test_row_count_matches_merged_dataset(
    enriched_df: pd.DataFrame, merged_df: pd.DataFrame
) -> None:
    """enrich() is a left join and raises internally if the row count changes,
    but that guard only fires on a live pipeline run. This checks the file
    actually on disk still reflects that invariant."""
    assert len(enriched_df) == len(merged_df), (
        f"Row count differs between merged ({len(merged_df)}) and enriched "
        f"({len(enriched_df)}) datasets on disk. Was enriched_dataset.csv "
        f"regenerated from the current merged_dataset.csv?"
    )


# ==========================================================================
# 4. Patient-level identity and uniqueness
# ==========================================================================


def test_patient_id_not_missing(enriched_df: pd.DataFrame) -> None:
    assert COLNAME_PATIENT_ID in enriched_df.columns, f"'{COLNAME_PATIENT_ID}' column absent."
    n_missing = enriched_df[COLNAME_PATIENT_ID].isna().sum()
    assert n_missing == 0, f"{n_missing} row(s) have a missing '{COLNAME_PATIENT_ID}'."


def test_patient_visit_rows_are_unique(enriched_df: pd.DataFrame) -> None:
    """(STUDY_ID, patient_id, follow_up_months) must uniquely identify a row.

    A duplicate here means either the same patient-visit was loaded twice,
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


# ==========================================================================
# 5. follow_up_months integrity
# ==========================================================================


def test_follow_up_months_is_numeric(enriched_df: pd.DataFrame) -> None:
    if COLNAME_FOLLOW_UP not in enriched_df.columns:
        pytest.skip(f"'{COLNAME_FOLLOW_UP}' column absent.")
    non_numeric = pd.to_numeric(enriched_df[COLNAME_FOLLOW_UP], errors="coerce")
    bad_mask = non_numeric.isna() & enriched_df[COLNAME_FOLLOW_UP].notna()
    assert not bad_mask.any(), (
        f"{bad_mask.sum()} non-numeric '{COLNAME_FOLLOW_UP}' value(s): "
        f"{sorted(enriched_df.loc[bad_mask, COLNAME_FOLLOW_UP].unique())[:10]}"
    )


def test_follow_up_months_not_negative(enriched_df: pd.DataFrame) -> None:
    if COLNAME_FOLLOW_UP not in enriched_df.columns:
        pytest.skip(f"'{COLNAME_FOLLOW_UP}' column absent.")
    values = pd.to_numeric(enriched_df[COLNAME_FOLLOW_UP], errors="coerce").dropna()
    negative = values[values < 0]
    assert negative.empty, (
        f"{len(negative)} negative '{COLNAME_FOLLOW_UP}' value(s): "
        f"{sorted(negative.unique())[:10]}"
    )


def test_baseline_follow_up_represented_consistently(enriched_df: pd.DataFrame) -> None:
    """Every study should use the same value to mean 'baseline' (typically
    0). If some studies encode baseline as 0 and others don't have a 0 row
    at all, that's worth investigating -- it may mean baseline was dropped
    for some studies, or coded with a different value (e.g. 1).

    This is a report, not a hard failure, since a study design that starts
    follow-up at a non-zero month is legitimate.
    """
    needed = [COLNAME_STUDYID, COLNAME_FOLLOW_UP]
    if any(c not in enriched_df.columns for c in needed):
        pytest.skip(f"Missing column(s): {needed}")

    min_by_study = enriched_df.groupby(COLNAME_STUDYID)[COLNAME_FOLLOW_UP].min()
    non_zero_baseline = sorted(min_by_study[min_by_study != 0].index)

    if non_zero_baseline:
        pytest.skip(
            f"{len(non_zero_baseline)} study/studies do not have a "
            f"'{COLNAME_FOLLOW_UP}' == 0 row (minimum observed instead): \n"
            f"{min_by_study.loc[non_zero_baseline]}"
        )


def test_follow_up_months_within_reasonable_bound(enriched_df: pd.DataFrame) -> None:
    """Collaborative-care depression trials rarely follow patients beyond a
    few years. A value far beyond that is more likely a unit error (e.g.
    days or weeks mistakenly loaded as months) than a real follow-up point.

    UPPER_BOUND is a sanity ceiling, not a study-design cutoff -- raise it
    if you have a study with a legitimately long follow-up.
    """
    if COLNAME_FOLLOW_UP not in enriched_df.columns:
        pytest.skip(f"'{COLNAME_FOLLOW_UP}' column absent.")
    UPPER_BOUND_MONTHS = 60
    values = pd.to_numeric(enriched_df[COLNAME_FOLLOW_UP], errors="coerce").dropna()
    too_high = values[values > UPPER_BOUND_MONTHS]
    if not too_high.empty:
        pytest.skip(
            f"{len(too_high)} '{COLNAME_FOLLOW_UP}' value(s) exceed the "
            f"{UPPER_BOUND_MONTHS}-month sanity ceiling: "
            f"{sorted(too_high.unique())[:10]}. Confirm these are real "
            f"follow-up points, not a unit mismatch."
        )


# ==========================================================================
# 6. Study-level enrichment / treatment-column correctness
# ==========================================================================


def test_treatment_columns_exist_and_are_prefixed(
    enriched_df: pd.DataFrame, treatment_cols: list[str]
) -> None:
    """Every non-join-key column from the extra-info sheet should show up
    under the treatment_ namespace, matching enrich()'s renaming."""
    extra_infos = load_study_level_extra_infos()
    drop_cols = ["No", "Study ID", "Treatment Group", "HANNAH_Study/Row Id", "HANNAH_StudyNo"]
    sheet_feature_cols = [
        c
        for c in extra_infos.columns
        if c not in drop_cols and c not in (COLNAME_EXTRA_INFO_STUDYID, "treatment_id")
    ]

    assert treatment_cols, "No 'treatment_*' columns found in enriched_dataset.csv."

    expected = {f"{TREATMENT_COL_PREFIX}{c}" for c in sheet_feature_cols}
    actual = set(treatment_cols)
    assert expected == actual, (
        f"Mismatch between sheet-derived treatment columns and enriched output:\n"
        f"  expected but missing: {sorted(expected - actual)}\n"
        f"  present but unexpected: {sorted(actual - expected)}"
    )


def test_control_arms_of_sheet_studies_are_filled_no(
    enriched_df: pd.DataFrame, treatment_cols: list[str]
) -> None:
    """Control arms of studies present in the extra-info sheet must have
    'no' (not NaN) for every treatment_* column -- that's the whole point
    of the control-arm fill step in enrich()."""
    extra_infos = load_study_level_extra_infos()
    sheet_study_ids = set(extra_infos[COLNAME_EXTRA_INFO_STUDYID])

    in_sheet = enriched_df[COLNAME_STUDYID].isin(sheet_study_ids)
    is_control = in_sheet & enriched_df[COLNAME_STUDY_ARM].eq(CONTROL_STUDY_ARM)

    if not is_control.any():
        pytest.skip("No control-arm rows for in-sheet studies to check.")

    control_block = enriched_df.loc[is_control, treatment_cols]
    not_no = control_block.apply(lambda col: col.ne("no")).any(axis=1)
    bad_rows = enriched_df.loc[is_control].loc[not_no]

    assert bad_rows.empty, (
        f"{len(bad_rows)} control-arm row(s) of in-sheet studies have a "
        f"treatment_* value other than 'no':\n"
        f"{bad_rows[[COLNAME_STUDYID, COLNAME_STUDY_ARM] + treatment_cols].head()}"
    )


def test_studies_absent_from_sheet_are_all_nan(
    enriched_df: pd.DataFrame, treatment_cols: list[str]
) -> None:
    """Studies with no match in the extra-info sheet should keep NaN across
    every treatment_* column (both arms) -- they must NOT get silently
    defaulted to 'no' or any other value."""
    extra_infos = load_study_level_extra_infos()
    sheet_study_ids = set(extra_infos[COLNAME_EXTRA_INFO_STUDYID])

    not_in_sheet = ~enriched_df[COLNAME_STUDYID].isin(sheet_study_ids)
    if not not_in_sheet.any():
        pytest.skip("Every study in the enriched output is present in the extra-info sheet.")

    block = enriched_df.loc[not_in_sheet, treatment_cols]
    has_any_value = block.notna().any(axis=1)
    bad_rows = enriched_df.loc[not_in_sheet].loc[has_any_value]

    assert bad_rows.empty, (
        f"{len(bad_rows)} row(s) of studies absent from the extra-info sheet "
        f"unexpectedly have non-NaN treatment_* value(s):\n"
        f"{bad_rows[[COLNAME_STUDYID, COLNAME_STUDY_ARM] + treatment_cols].head()}"
    )


def test_enriched_file_matches_live_enrich_output(merged_df: pd.DataFrame) -> None:
    """Regenerate enrichment from the merged dataset currently on disk and
    diff it against the saved enriched_dataset.csv, to catch a stale file
    that wasn't rebuilt after a code or data change."""
    live_df = enrich(merged_df.copy())

    if not ENRICHED_CSV.exists():
        pytest.skip(f"{ENRICHED_CSV} not found.")
    saved_df = pd.read_csv(ENRICHED_CSV)

    # Round-trip the live result through CSV so dtypes match what's on disk
    # (e.g. everything read back as string/NaN the same way).
    import io

    buf = io.StringIO()
    live_df.to_csv(buf, index=False)
    buf.seek(0)
    live_df_roundtripped = pd.read_csv(buf)

    pd.testing.assert_frame_equal(
        saved_df.reset_index(drop=True),
        live_df_roundtripped.reset_index(drop=True),
        check_like=True,
    )


# ==========================================================================
# 7. PHQ-9 item/total consistency
# ==========================================================================


def test_phq9_items_in_range(enriched_df: pd.DataFrame) -> None:
    present = _present(enriched_df, PHQ9_ITEMS)
    if not present:
        pytest.skip("No phq9_1..9 item columns present.")
    for col in present:
        _assert_in_range(enriched_df[col], 0, 3, col)


def test_phq9_total_in_range(enriched_df: pd.DataFrame) -> None:
    if "phq9_total" in enriched_df.columns:
        _assert_in_range(enriched_df["phq9_total"], 0, 27, "phq9_total")


def test_phq9_total_matches_item_sum(enriched_df: pd.DataFrame) -> None:
    """Where both the 9 items and a total are present, the total should
    equal the item sum for rows with no missing items."""
    items_present = _present(enriched_df, PHQ9_ITEMS)
    if len(items_present) != 9 or "phq9_total" not in enriched_df.columns:
        pytest.skip("Need all 9 phq9 items plus phq9_total to check consistency.")

    complete_rows = (
        enriched_df[items_present].notna().all(axis=1) & enriched_df["phq9_total"].notna()
    )
    if not complete_rows.any():
        pytest.skip("No rows with both complete items and a total to compare.")

    computed = enriched_df.loc[complete_rows, items_present].sum(axis=1)
    stated = enriched_df.loc[complete_rows, "phq9_total"]
    mismatch = complete_rows[complete_rows].index[computed.round(0) != stated.round(0)]

    assert len(mismatch) == 0, (
        f"{len(mismatch)} row(s) where phq9_total doesn't match the sum of "
        f"phq9_1..9. Example row indices: {list(mismatch[:5])}"
    )


def test_no_duplicate_phq9_total_column_reappears(enriched_df: pd.DataFrame) -> None:
    """phq9_total.1 was a duplicate-column artifact from an earlier
    harmonization naming collision (two scripts independently producing a
    PHQ-9 total, merged into two separate columns instead of one). That has
    since been fixed upstream and the column no longer appears. This test
    guards against it silently reappearing in a future pipeline run."""
    assert "phq9_total.1" not in enriched_df.columns, (
        "'phq9_total.1' has reappeared in enriched_dataset.csv. This was "
        "previously caused by two harmonization scripts writing a PHQ-9 "
        "total under slightly different names. Check which loader/"
        "harmonization script reintroduced it."
    )


def test_phq9_items_imply_phq9_total(enriched_df: pd.DataFrame) -> None:
    """A row with all 9 PHQ-9 items answered should also have a PHQ-9 total
    -- a fully-answered PHQ-9 with no total suggests the harmonization/
    scoring step for that study didn't run or was skipped.
    """
    items_present = _present(enriched_df, PHQ9_ITEMS)
    totals_present = _present(enriched_df, PHQ9_TOTAL_CANDIDATES)

    if len(items_present) != len(PHQ9_ITEMS):
        pytest.skip(
            f"Not all 9 phq9 item columns present (found {items_present}); "
            f"skipping the complete-row check."
        )
    if not totals_present:
        pytest.fail(
            f"All 9 phq9 item columns are present but no total column "
            f"({PHQ9_TOTAL_CANDIDATES}) exists at all."
        )

    has_all_items = enriched_df[items_present].notna().all(axis=1)
    has_any_total = enriched_df[totals_present].notna().any(axis=1)

    missing_total = has_all_items & ~has_any_total
    assert not missing_total.any(), (
        f"{missing_total.sum()} row(s) have all 9 phq9 items answered but "
        f"no phq9 total in any of {totals_present}."
    )


# ==========================================================================
# 8. Other depression-instrument range checks
# ==========================================================================


def test_gad7_items_in_range(enriched_df: pd.DataFrame) -> None:
    present = _present(enriched_df, GAD7_ITEMS)
    if not present:
        pytest.skip("No gad7_1..7 item columns present.")
    for col in present:
        _assert_in_range(enriched_df[col], 0, 3, col)


def test_gad7_total_in_range(enriched_df: pd.DataFrame) -> None:
    if "gad7_total" in enriched_df.columns:
        _assert_in_range(enriched_df["gad7_total"], 0, 21, "gad7_total")


def test_k10_total_in_range(enriched_df: pd.DataFrame) -> None:
    if "k10_total" in enriched_df.columns:
        _assert_in_range(enriched_df["k10_total"], 10, 50, "k10_total")


def test_hrsd17_total_in_range(enriched_df: pd.DataFrame) -> None:
    if "hrsd17_total" in enriched_df.columns:
        _assert_in_range(enriched_df["hrsd17_total"], 0, 52, "hrsd17_total")


def test_hrsd17_suicide_item_in_range(enriched_df: pd.DataFrame) -> None:
    """The HRSD-17 suicide item is scored 0-4."""
    if "hrsd17_suicide_item" in enriched_df.columns:
        _assert_in_range(enriched_df["hrsd17_suicide_item"], 0, 4, "hrsd17_suicide_item")


def test_hscl_total_in_range(enriched_df: pd.DataFrame) -> None:
    """hscl_total here appears to be a mean-item score (typical HSCL-D scoring
    is a 1-4 average, not a raw sum). Adjust bounds if your codebook defines
    hscl_total as a raw sum instead."""
    if "hscl_total" in enriched_df.columns:
        _assert_in_range(enriched_df["hscl_total"], 1, 4, "hscl_total")


def test_cisr_total_in_range(enriched_df: pd.DataFrame) -> None:
    if "cisr_total" in enriched_df.columns:
        _assert_in_range(enriched_df["cisr_total"], 0, 57, "cisr_total")


def test_promis_depression_tscore_in_range(enriched_df: pd.DataFrame) -> None:
    if "promis_depression_tscore" in enriched_df.columns:
        _assert_in_range(
            enriched_df["promis_depression_tscore"], 15, 100, "promis_depression_tscore"
        )


# ==========================================================================
# 9. Suicidality-field sanity
# ==========================================================================


def test_suicidality_related_columns_are_binary_or_categorical(enriched_df: pd.DataFrame) -> None:
    """These columns should hold a small, closed set of category codes (e.g.
    yes/no or 0/1), not free text or out-of-scale numerics -- a sign that
    harmonization mapped raw source codes incorrectly."""
    cols = _present(
        enriched_df,
        ["suicidal_ideation", "suicidal_plan", "suicide_attempt", "hscl_suicidal"],
    )
    if not cols:
        pytest.skip("No suicidality-related columns present.")

    for col in cols:
        n_unique = enriched_df[col].dropna().nunique()
        assert n_unique <= 10, (
            f"{col} has {n_unique} distinct non-null value(s) -- expected a "
            f"small closed set (binary/categorical). Values seen: "
            f"{sorted(enriched_df[col].dropna().unique())[:10]}"
        )


# ==========================================================================
# 10. Cross-instrument sanity
# ==========================================================================


def test_every_row_has_at_least_one_depression_measure(enriched_df: pd.DataFrame) -> None:
    """Every patient-visit row should have a non-null value in at least one
    depression instrument's total score -- otherwise that row contributes
    nothing to any depression-outcome analysis."""
    present = _present(enriched_df, DEPRESSION_TOTAL_COLS)
    if not present:
        pytest.skip("No depression total-score columns present.")

    has_any = enriched_df[present].notna().any(axis=1)
    n_missing = (~has_any).sum()
    if n_missing > 0:
        pct = 100 * n_missing / len(enriched_df)
        pytest.skip(
            f"{n_missing} row(s) ({pct:.1f}%) have no depression measure at all "
            f"across {present}. This is reported, not failed, since some "
            f"study-visits may legitimately not administer a depression scale."
        )


# ==========================================================================
# 11. Column-level hygiene: duplicates, empty, constant
# ==========================================================================


def test_no_duplicate_column_names(enriched_df: pd.DataFrame) -> None:
    names = list(enriched_df.columns)
    dupes = sorted({c for c in names if names.count(c) > 1})
    assert not dupes, f"Duplicate column name(s): {dupes}"


def test_no_duplicate_column_content(enriched_df: pd.DataFrame) -> None:
    """Two differently-named columns with identical content in every row are
    almost always the same variable produced twice by different
    harmonization scripts (see the phq9_total / phq9_total.1 case)."""
    seen: dict[tuple, str] = {}
    dupes: list[tuple[str, str]] = []
    for col in enriched_df.columns:
        fingerprint = tuple(enriched_df[col].fillna("<NA>").astype(str))
        if fingerprint in seen:
            dupes.append((seen[fingerprint], col))
        else:
            seen[fingerprint] = col

    if dupes:
        pytest.skip(f"Column(s) with identical content to an earlier column: {dupes}")


def test_no_fully_empty_columns(enriched_df: pd.DataFrame) -> None:
    empty_cols = [c for c in enriched_df.columns if enriched_df[c].isna().all()]
    assert not empty_cols, (
        f"{len(empty_cols)} fully-empty (all-NaN) column(s): {empty_cols}. "
        f"Likely a harmonization script that writes the column but never "
        f"populates it, or a join that never matched."
    )


def test_no_constant_columns(enriched_df: pd.DataFrame) -> None:
    """A column with exactly one distinct non-null value carries no
    information for analysis and may indicate a hardcoded/default value
    that was supposed to vary."""
    constant_cols = [c for c in enriched_df.columns if enriched_df[c].nunique(dropna=True) == 1]
    if constant_cols:
        details = {c: enriched_df[c].dropna().iloc[0] for c in constant_cols}
        pytest.skip(f"Column(s) with only one distinct value: {details}")


# ==========================================================================
# 12. Missingness report (diagnostic only)
# ==========================================================================


def test_missingness_report(enriched_df: pd.DataFrame) -> None:
    """Diagnostic report of missingness at four levels. Never fails on its
    own (missingness is expected in a pooled multi-study dataset) -- it
    exists to surface the breakdown in test output, e.g. via
    `pytest -s tests/test_enrichment.py::test_missingness_report`.
    """
    overall = enriched_df.isna().mean().sort_values(ascending=False)

    by_study = (
        enriched_df.groupby(COLNAME_STUDYID).apply(lambda g: g.isna().mean())
        if COLNAME_STUDYID in enriched_df.columns
        else None
    )
    by_arm = (
        enriched_df.groupby(COLNAME_STUDY_ARM).apply(lambda g: g.isna().mean())
        if COLNAME_STUDY_ARM in enriched_df.columns
        else None
    )
    by_follow_up = (
        enriched_df.groupby(COLNAME_FOLLOW_UP).apply(lambda g: g.isna().mean())
        if COLNAME_FOLLOW_UP in enriched_df.columns
        else None
    )

    logger.info(f"Overall missingness (top 10):\n{overall.head(10)}")
    if by_study is not None:
        logger.info(f"Missingness by study (mean across columns):\n{by_study.mean(axis=1)}")
    if by_arm is not None:
        logger.info(f"Missingness by arm (mean across columns):\n{by_arm.mean(axis=1)}")
    if by_follow_up is not None:
        logger.info(
            f"Missingness by follow-up month (mean across columns):\n{by_follow_up.mean(axis=1)}"
        )

    pytest.skip(
        "Missingness report generated (see log output with -s); this test "
        "is diagnostic only and does not assert a threshold."
    )
