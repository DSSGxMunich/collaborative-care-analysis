from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Davidson 2013 = the CODIACS Vanguard RCT. Patients recruited 2-6 months after
# an acute coronary syndrome with Beck Depression Inventory (BDI-I) score >=10;
# randomised 1:1 to "Stepped Care" (centralised, stepped, patient-preference
# depression care: problem-solving therapy and/or pharmacotherapy) vs "Referred
# Care" (local physician). N = 150. BDI, health-care use and medication use were
# assessed at baseline and 6 months in person and at 2 and 4 months by phone.
# Primary outcomes: change in BDI over 6 months and health-care costs.
#
# The raw file is wide: one row per patient, repeated measures encoded as column
# suffixes ``_bl`` / ``_2m`` / ``_4m`` / ``_6m``. This loader stacks those into
# long format (one row per patient-visit). Columns with no timepoint suffix are
# treated as time-invariant and broadcast to every visit row.

ID_COL = "SUBJID"

SUFFIX_TO_MONTHS = {
    "_bl": 0,
    "_2m": 2,
    "_4m": 4,
    "_6m": 6,
}

# CODIACS required two elevated BDI readings to confirm persistent depression,
# so both are genuine baseline measurements and both are kept.
BASELINE_BDI_COLS = ("bdiscore_01", "bdiscore_02")

# Columns that are non-negative by definition. Sibling columns in this export
# encode missingness with negative sentinels (``-1``, ``-3``), so a negative
# value in one of these is missingness, not data. This is a declared list rather
# than a blanket rule over every numeric column on purpose: legitimately signed
# quantities such as change scores must keep their sign.
NON_NEGATIVE_COLS = ("charlson_comorbidity_index",)


def _wide_columns_for(df: pd.DataFrame, stem: str) -> list[str]:
    """Wide columns belonging to ``stem``: the bare name plus any suffixed visits."""
    candidates = (stem, *(f"{stem}{suffix}" for suffix in SUFFIX_TO_MONTHS))
    return [col for col in candidates if col in df.columns]


def sentinels_to_na(df: pd.DataFrame) -> pd.DataFrame:
    """Replace negative missing sentinels with ``pd.NA`` in the non-negative columns."""
    df = df.copy()

    for stem in NON_NEGATIVE_COLS:
        columns = _wide_columns_for(df, stem)
        if not columns:
            raise ValueError(f"Declared non-negative column is absent from the export: {stem!r}")

        for col in columns:
            # errors="raise": a value that will not parse means the export
            # changed, and we want to hear about it rather than have it
            # silently coerced to <NA> and counted as missing data.
            values = pd.to_numeric(df[col], errors="raise")

            sentinel = (values < 0).fillna(False)
            n_sentinel = int(sentinel.sum())
            if n_sentinel:
                observed = sorted(values[sentinel].unique().tolist())
                logger.warning(
                    f"{col}: replaced {n_sentinel} negative missing sentinel(s) "
                    f"{observed} with <NA>"
                )

            df[col] = values.mask(sentinel)

    return df.convert_dtypes()


def check_baseline_bdi(df: pd.DataFrame) -> None:
    """Validate that both baseline BDI readings are present and will be broadcast."""
    absent = [col for col in BASELINE_BDI_COLS if col not in df.columns]
    if absent:
        raise ValueError(f"Expected baseline BDI column(s) missing from the export: {absent}")

    # A suffixed baseline reading would mean the export now fills month 0 through
    # the stacking itself, which would make the handling here stale and silently
    # change what "baseline BDI" refers to downstream.
    conflicting = [col for col in df.columns if col.startswith("bdiscore") and col.endswith("_bl")]
    if conflicting:
        raise ValueError(
            f"Export now carries a suffixed baseline BDI column ({conflicting}); "
            "revisit how baseline BDI is represented before loading."
        )

    logger.warning(
        "CODIACS required two elevated BDIs to confirm persistent depression, so both are "
        "broadcast to every visit row."
    )


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Stack the ``_bl`` / ``_2m`` / ``_4m`` / ``_6m`` visits into long format."""
    # stem -> {suffix: column name}
    time_varying: dict[str, dict[str, str]] = {}
    for col in df.columns:
        if col == ID_COL:
            continue
        for suffix in SUFFIX_TO_MONTHS:
            if col.endswith(suffix):
                time_varying.setdefault(col[: -len(suffix)], {})[suffix] = col
                break

    matched = {c for mapping in time_varying.values() for c in mapping.values()}
    static_cols = [c for c in df.columns if c != ID_COL and c not in matched]

    collisions = set(time_varying) & set(static_cols)
    if collisions:
        raise ValueError(f"stem name also used as a static column: {sorted(collisions)}")

    frames = []
    for suffix, months in SUFFIX_TO_MONTHS.items():
        # Only carry stems that were actually measured at this visit; pd.concat
        # aligns on column name and fills the rest with NaN.
        renames = {
            by_suffix[suffix]: stem
            for stem, by_suffix in time_varying.items()
            if suffix in by_suffix
        }
        visit = df[[ID_COL, *static_cols, *renames]].rename(columns=renames)
        visit.insert(1, "follow_up_months", months)
        frames.append(visit)

    long = (
        pd.concat(frames, ignore_index=True, sort=False)
        .rename(columns={ID_COL: "patient_id"}, errors="raise")
        .sort_values(["patient_id", "follow_up_months"], kind="stable")
        .reset_index(drop=True)
    )

    if long.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    head = ["patient_id", "follow_up_months"]
    return long[head + [c for c in long.columns if c not in head]].convert_dtypes()


def load(file_path=RAW_DATASETS_DIR / "09_Davidson_2013" / "Davidson 2013 CLEANED.sav"):
    df = pd.read_spss(file_path, convert_categoricals=False).convert_dtypes()

    missing_id = df[ID_COL].isna()
    if missing_id.any():
        logger.warning(f"Removed {int(missing_id.sum())} rows with missing {ID_COL}")
        df = df.loc[~missing_id]

    if df[ID_COL].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    df = sentinels_to_na(df)
    check_baseline_bdi(df)

    return to_long(df)
