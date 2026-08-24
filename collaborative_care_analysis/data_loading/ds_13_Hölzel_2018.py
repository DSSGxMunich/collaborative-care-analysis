"""
Pipeline
--------
1.  normalise known column-name defects
2.  partition the raw columns into time-independent / time-dependent, and
    assert the partition is exhaustive and disjoint
3.  verify the stored PHQ-9 totals are recoverable from the nine items
4.  warn about and drop the contradicted patients, then drop every stored total
5.  stack the three visits into long format with generic column names

The FIMA medication slots stay wide (``FIMA_Med1_Name`` ... ``FIMA_Med18_PZN``),
which is what keeps the grain at one row per (patient_id, follow_up_months).
"""

import re

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR  # <- adjust to wherever this lives

TIMEPOINT_TO_MONTHS = {"B1": 0, "B2": 6, "B3": 12}

TIME_DEPENDENT_PREFIX = re.compile(rf"^GI_(?:{'|'.join(TIMEPOINT_TO_MONTHS)})_")

UNPREFIXED_TIME_DEPENDENT_COLS = [
    "PHQ_0_Monate",
    "PHQ_6_Monate",
    "PHQ_12_Monate",
]

RAW_TIME_INDEPENDENT_COLS = [
    "ID",
    "v_zentrum",
    "Cluster",
    "RG",
    "PIN",
    "GI_B1_Alter",
    "GI_B1_Geschlecht",
    "GI_B1_Bildung",
    "GI_B1_Anstellung",
    "GI_B1_Erwerbsumfang",
    "GI_B1_Geld_aureichend",
]

# Med8_Groesse is misspelled at every timepoint.
COLUMN_NAME_FIXES = {
    f"GI_{tp}_FIMA_med8_Groesse": f"GI_{tp}_FIMA_Med8_Groesse" for tp in TIMEPOINT_TO_MONTHS
}

# applied after reshaping, on the long frame
ANALYSIS_NAMES = {
    "ID": "patient_id",
    "RG": "study_arm",
}

PHQ9_ITEM_NUMBERS = range(1, 10)

STORED_PHQ_TOTALS = {
    **{f"PHQ_{months}_Monate": tp for tp, months in TIMEPOINT_TO_MONTHS.items()},
    "GI_B3_PHQ_Gesamt": "B3",
}

GRAIN = ["patient_id", "follow_up_months"]

PHQ_REPORT_COLUMNS = [
    "total_column",
    "timepoint",
    "n_comparable",
    "n_mismatched",
    "n_unrecoverable",
    "recoverable",
]

PHQ_DISCREPANCY_COLUMNS = ["patient_id", "total_column", "timepoint", "stored", "computed"]


def normalise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Repair the spelling defects in the raw export."""
    return df.rename(columns=COLUMN_NAME_FIXES, errors="raise")


def partition_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Split the raw columns into (time-independent, time-dependent)."""
    time_dependent = [
        col
        for col in df.columns
        if col not in RAW_TIME_INDEPENDENT_COLS
        and (TIME_DEPENDENT_PREFIX.match(col) or col in UNPREFIXED_TIME_DEPENDENT_COLS)
    ]

    independent, dependent = set(RAW_TIME_INDEPENDENT_COLS), set(time_dependent)
    present = set(df.columns)

    if overlap := independent & dependent:
        raise ValueError(f"columns classified as both: {sorted(overlap)}")
    if absent := (independent | dependent) - present:
        raise ValueError(f"expected columns missing from the export: {sorted(absent)}")
    if unaccounted := present - (independent | dependent):
        raise ValueError(f"columns fit neither partition: {sorted(unaccounted)}")

    return list(RAW_TIME_INDEPENDENT_COLS), time_dependent


def check_phq_totals(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Test whether each stored PHQ-9 total equals the sum of its nine items."""
    rows = []
    discrepancy_frames = []

    for total_col, timepoint in STORED_PHQ_TOTALS.items():
        item_cols = [f"GI_{timepoint}_PHQ9_{i}" for i in PHQ9_ITEM_NUMBERS]
        if total_col not in df.columns or not set(item_cols) <= set(df.columns):
            continue
        items = df[item_cols]
        if non_numeric := [
            c for c in items.columns if not pd.api.types.is_numeric_dtype(items[c])
        ]:
            raise TypeError(
                f"PHQ-9 items are not numeric ({non_numeric[0]!r}: "
                f"{items[non_numeric[0]].dtype}, ...) and cannot be summed. Read the "
                "score items as codes (convert_categoricals=False) or map the labels "
                "back to 0-3 before running this check."
            )

        computed = items.sum(axis=1, min_count=len(PHQ9_ITEM_NUMBERS))
        stored = df[total_col]

        comparable = computed.notna() & stored.notna()
        # both values present and disagreeing: the questionnaire contradicts itself
        mismatched = comparable & (computed != stored)
        # stored but not reproducible, so dropping the column loses it. Not a
        # contradiction, so it does not cost the patient their row.
        unrecoverable = stored.notna() & computed.isna()

        if mismatched.any():
            discrepancy_frames.append(
                pd.DataFrame(
                    {
                        "patient_id": df.loc[mismatched, "ID"],
                        "total_column": total_col,
                        "timepoint": timepoint,
                        "stored": stored[mismatched],
                        "computed": computed[mismatched],
                    }
                )
            )

        rows.append(
            {
                "total_column": total_col,
                "timepoint": timepoint,
                "n_comparable": int(comparable.sum()),
                "n_mismatched": int(mismatched.sum()),
                "n_unrecoverable": int(unrecoverable.sum()),
                "recoverable": bool(mismatched.sum() == 0 and unrecoverable.sum() == 0),
            }
        )

    discrepancies = (
        pd.concat(discrepancy_frames)
        if discrepancy_frames
        else pd.DataFrame(columns=PHQ_DISCREPANCY_COLUMNS)
    )
    # explicit columns so an empty report still has a 'recoverable' column
    return pd.DataFrame(rows, columns=PHQ_REPORT_COLUMNS), discrepancies


def drop_checked_totals(
    df: pd.DataFrame, report: pd.DataFrame, discrepancies: pd.DataFrame
) -> pd.DataFrame:
    """Drop the contradicted patients, then drop every stored PHQ-9 total."""
    for total_col, group in discrepancies.groupby("total_column", sort=False):
        logger.warning(
            "Stored PHQ-9 total '{}' contradicts its nine items for {} patient(s): {}",
            total_col,
            len(group),
            group["patient_id"].tolist(),
        )

    if not discrepancies.empty:
        contradicted = discrepancies.index.unique()
        logger.warning(
            "Dropping {} of {} patient records with contradicted PHQ-9 totals.",
            len(contradicted),
            len(df),
        )
        df = df.drop(index=contradicted)

    # incomplete item sets are kept, but their stored total goes with the column
    for row in report.loc[report["n_unrecoverable"] > 0].itertuples(index=False):
        logger.info(
            "'{}' holds {} total(s) that cannot be recomputed from incomplete items; "
            "these are lost with the column.",
            row.total_column,
            row.n_unrecoverable,
        )

    return df.drop(columns=[c for c in STORED_PHQ_TOTALS if c in df.columns])


def to_long(df: pd.DataFrame, time_independent: list[str]) -> pd.DataFrame:
    """Stack the three visits, stripping the ``GI_B{t}_`` prefix from each stub."""
    time_varying = [c for c in df.columns if c not in time_independent]

    # anything without a visit prefix matches no frame below and would vanish
    if orphans := [c for c in time_varying if not TIME_DEPENDENT_PREFIX.match(c)]:
        raise ValueError(f"time-varying columns carry no visit prefix: {sorted(orphans)}")

    frames = []
    for timepoint, months in TIMEPOINT_TO_MONTHS.items():
        prefix = f"GI_{timepoint}_"
        visit_cols = [c for c in time_varying if c.startswith(prefix)]

        visit = df[time_independent + visit_cols].copy()
        stubs = [c.removeprefix("GI_B1_") for c in time_independent] + [
            c.removeprefix(prefix) for c in visit_cols
        ]
        # e.g. GI_B1_Alter (time-independent) and GI_B2_Alter both stack to Alter
        if len(set(stubs)) != len(stubs):
            collisions = sorted({s for s in stubs if stubs.count(s) > 1})
            raise ValueError(f"{prefix}: stub names collide after stripping: {collisions}")
        visit.columns = stubs
        visit.insert(len(time_independent), "follow_up_months", months)
        frames.append(visit)

    long = (
        pd.concat(frames, ignore_index=True)
        .rename(columns=ANALYSIS_NAMES, errors="raise")
        .sort_values(GRAIN, kind="stable")
        .reset_index(drop=True)
    )

    if long.duplicated(GRAIN).any():
        duplicates = long.loc[long.duplicated(GRAIN, keep=False), GRAIN]
        raise ValueError(
            f"grain violated: {len(duplicates)} duplicate {tuple(GRAIN)} rows, "
            f"first offender {tuple(duplicates.iloc[0])}"
        )

    first_columns = ["patient_id", "follow_up_months", "study_arm"]
    remaining_columns = [column for column in long.columns if column not in first_columns]
    return long[first_columns + remaining_columns]


def load(
    file_path=RAW_DATASETS_DIR
    / "13_Hölzel_2018"
    / "Daten"
    / "20231120_German_IMPACT_f__r_IPD_MA.sav",
) -> pd.DataFrame:
    """Run the full pipeline."""
    df = pd.read_spss(
        path=file_path,
        convert_categoricals=False,
    )
    df.replace(to_replace=r"^\s*$", value=pd.NA, inplace=True, regex=True)

    df = df.convert_dtypes()

    # Remove rows containing only missing values.
    df.dropna(how="all", axis="index", inplace=True)

    # Remove leading and trailing whitespace from column names.
    df.columns = df.columns.str.strip()

    df = normalise_column_names(df)
    time_independent, _ = partition_columns(df)

    phq_report, phq_discrepancies = check_phq_totals(df)
    df = drop_checked_totals(df, phq_report, phq_discrepancies)

    long = to_long(df, time_independent)
    long.dropna(how="all", axis="columns", inplace=True)

    return long
