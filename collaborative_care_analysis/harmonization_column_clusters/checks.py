"""Shared diagnostics for the cluster harmonization.

Every cluster reads columns whose meaning was reconstructed from codebooks,
papers and arithmetic. The failure mode that matters is not a crash: it is a
mapping that silently produces plausible-looking nonsense, such as a condition
flag that is never true, a scale read on the wrong range, or a source column
that quietly vanished from the export. These helpers make each of those loud.

Two rules, following AGENTS.md and the repo's own conventions:

* a **data** problem warns and drops to missing, so one bad study cannot stop
  the build for the other 29;
* a **code or schema** problem raises, because it means the module and the
  frame disagree about what exists, and every later number would be built on
  that disagreement.

Nothing here logs a value: counts, ranges and percentages only.
"""

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

# A harmonized column populated for fewer than this many patients in a study is
# reported. Not an error: some studies genuinely answer for a handful of people.
SPARSE_COVERAGE_THRESHOLD = 0.05


def require_columns(df: pd.DataFrame, study_id: str, columns: list[str], cluster: str) -> None:
    """Raise unless every source column this study declares is in the frame.

    A missing column means the module's per-study map and the exports have
    drifted apart, usually because a loader was renamed. Continuing would
    silently drop that study from the harmonized column.
    """
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"{cluster}/{study_id}: {missing} declared as source column(s) but absent "
            f"from the concatenated frame. Re-export, or fix the per-study map."
        )


def require_rows(df: pd.DataFrame, study_id: str, cluster: str) -> pd.Series:
    """Raise unless the study has rows at all, and return its row mask."""
    rows = df[COLNAME_STUDYID] == study_id
    if not rows.any():
        raise ValueError(
            f"{cluster}: {study_id!r} is mapped but has no rows in the frame. "
            f"Either the study id is misspelled or its export is missing."
        )
    return rows


def report_mapping(
    cluster: str, study_id: str, column: str, source: pd.Series, mapped: pd.Series
) -> None:
    """Log how much of a source column survived mapping, and warn if little did."""
    available = int(source.notna().sum())
    kept = int(mapped.notna().sum())
    if available == 0:
        logger.warning(
            f"{cluster}/{study_id}: source column {column!r} is entirely empty in the "
            f"export, so this study contributes nothing here."
        )
        return
    lost = available - kept
    if lost < 0:
        logger.debug(
            f"{cluster}/{study_id}: {column!r} produced {kept} value(s) from "
            f"{available} source value(s); the column is derived, not read directly."
        )
        return
    if lost:
        logger.warning(
            f"{cluster}/{study_id}: {column!r} had {available} value(s), {lost} of which "
            f"({100 * lost / available:.1f}%) did not map and are now missing."
        )
    else:
        logger.debug(f"{cluster}/{study_id}: {column!r} mapped {kept}/{available}.")


def check_range(
    values: pd.Series, bounds: tuple[float, float], cluster: str, what: str
) -> pd.Series:
    """Null out values outside an instrument's defined range, loudly."""
    outside = values.notna() & ~values.between(*bounds)
    if outside.any():
        logger.warning(
            f"{cluster}/{what}: {int(outside.sum())} value(s) outside {bounds} "
            f"(observed {values.min()} to {values.max()}) set to missing."
        )
    return values.where(~outside)


def check_degenerate(values: pd.Series, cluster: str, column: str, study_id: str) -> None:
    """Report a per-study result that is suspiciously uniform or empty.

    All-missing, always-true and always-false are each usually a mapping that
    matched nothing or everything, which looks like real data downstream.
    """
    answered = values.dropna()
    if answered.empty:
        logger.warning(f"{cluster}/{study_id}: {column!r} is missing for every row of this study.")
        return
    if answered.nunique() == 1 and len(answered) >= 30:
        logger.warning(
            f"{cluster}/{study_id}: {column!r} takes one value for all "
            f"{len(answered)} answered rows, which usually means the mapping matched "
            f"everything or nothing."
        )


def check_within_patient_constant(
    df: pd.DataFrame, values: pd.Series, cluster: str, column: str
) -> None:
    """Report patients whose supposedly baseline value changes between visits."""
    distinct = values.groupby([df[COLNAME_STUDYID], df["patient_id"]]).nunique(dropna=True)
    varying = distinct[distinct > 1]
    if not varying.empty:
        by_study = varying.groupby(level=0).size().to_dict()
        logger.warning(
            f"{cluster}: {column!r} is meant to be a baseline attribute but varies "
            f"within {len(varying)} patient(s): {by_study}."
        )


# Statistical packages encode missing as very large numbers, and a date read as
# a number looks like one. Stata: byte 101, int 32741, long 2147483621, float
# 1.7e38, double 8.99e307. A Unix timestamp is around 1.5e9 and a Stata date
# around 2e4. None of those belongs in a clinical measurement.
# The byte band, 101 to 127, is deliberately absent: a systolic blood pressure
# of 120 or a weight of 105 lives there, so testing it would cry wolf on real
# measurements. The other four are far outside any clinical range.
STATA_SENTINELS = {
    "int": 32741,
    "long": 2147483621,
    "float": 1.7014118346046923e38,
    "double": 8.98846567431158e307,
}
IMPLAUSIBLE_MAGNITUDE = 1e6


def check_magnitude(values: pd.Series, cluster: str, study_id: str, column: str) -> None:
    """Report values too large to be a clinical measurement.

    Catches two things that look identical in a CSV: a statistical package's
    missing-value encoding, and a date or identifier read as a number. ds_10's
    `withdraw` is a Unix timestamp near 1.5e9, and reading it as a quantity
    would put a billion into a regression.
    """
    numeric = pd.to_numeric(values, errors="coerce")
    if not numeric.notna().any():
        return
    # Sentinel bands are checked whatever the column's magnitude, because the
    # int band sits below the threshold at which a number merely looks odd.
    # Stata reserves exactly 27 missing codes per type, "." and ".a" to ".z",
    # running from the threshold upward. A value merely larger than a threshold
    # is not a sentinel: 1.5e9 exceeds the int threshold by five orders of
    # magnitude and is a Unix timestamp, not a missing marker.
    for kind, threshold in STATA_SENTINELS.items():
        in_band = numeric.abs().between(threshold, threshold + 26)
        if in_band.any():
            logger.warning(
                f"{cluster}/{study_id}: {column!r} has {int(in_band.sum())} value(s) in "
                f"the Stata {kind} missing-value band ({threshold:.6g} to "
                f"{threshold + 26:.6g}). These are missing markers read as numbers."
            )
            return

    largest = numeric.abs().max()
    if largest < IMPLAUSIBLE_MAGNITUDE:
        return
    logger.warning(
        f"{cluster}/{study_id}: {column!r} reaches {largest:.4g}, too large for a "
        f"clinical measurement. Values near 1.5e9 are Unix timestamps and values near "
        f"2e4 Stata dates; check whether this column is a date or an identifier."
    )


def summarize(df: pd.DataFrame, harmonized: pd.DataFrame, cluster: str) -> None:
    """Log one coverage line per harmonized column, and flag thin studies."""
    for column in harmonized.columns:
        if column in (COLNAME_STUDYID, "patient_id", "follow_up_months"):
            continue
        values = harmonized[column]
        studies = df.loc[values.notna(), COLNAME_STUDYID].nunique()
        logger.info(
            f"{cluster}: {column} -> {studies} study(ies), {int(values.notna().sum())} "
            f"row(s), dtype {values.dtype}."
        )
        for study_id, group in values.groupby(df[COLNAME_STUDYID]):
            if group.notna().any():
                check_degenerate(group, cluster, column, study_id)
                density = group.notna().mean()
                if density < SPARSE_COVERAGE_THRESHOLD:
                    logger.warning(
                        f"{cluster}/{study_id}: {column!r} is populated for only "
                        f"{100 * density:.1f}% of this study's rows."
                    )
