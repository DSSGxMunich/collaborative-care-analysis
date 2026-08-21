"""
Pipeline
--------
1.  normalise known column-name defects
2.  partition the raw columns into time-independent / time-dependent, and
    assert the partition is exhaustive and disjoint
3.  verify the stored PHQ-9 totals are recoverable from the nine items
4.  drop the redundant totals (only if step 3 passes)
5.  stack the three visits into long format with generic column names

The FIMA medication slots stay wide (``FIMA_Med1_Name`` ... ``FIMA_Med18_PZN``),
which is what keeps the grain at one row per (patient_id, follow_up_months).
"""

import re

import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR  # <- adjust to wherever this lives

TIMEPOINT_TO_MONTHS = {"B1": 0, "B2": 6, "B3": 12}

TIME_DEPENDENT_PREFIX = re.compile(r"^GI_B[123]_")

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


def normalise_column_names(df: pd.DataFrame):
    """Repair the spelling defects in the raw export."""
    return df.rename(columns=COLUMN_NAME_FIXES, errors="raise")


def partition_columns(df: pd.DataFrame):
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


def check_phq_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Test whether each stored PHQ-9 total equals the sum of its nine items."""
    stored_totals = {
        **{f"PHQ_{m}_Monate": tp for tp, m in TIMEPOINT_TO_MONTHS.items()},
        "GI_B3_PHQ_Gesamt": "B3",
    }

    rows = []
    for total_col, timepoint in stored_totals.items():
        if total_col not in df.columns:
            continue
        items = df[[f"GI_{timepoint}_PHQ9_{i}" for i in PHQ9_ITEM_NUMBERS]]

        # read_spss(convert_categoricals=True) returns labelled categoricals,
        # which cannot be summed. Fail with something actionable.
        if categorical := [
            c for c in items.columns if isinstance(items[c].dtype, pd.CategoricalDtype)
        ]:
            raise TypeError(
                f"PHQ-9 items are categorical ({categorical[0]!r}, ...) and cannot be "
                "summed. Read the score items as codes (convert_categoricals=False) "
                "or map the labels back to 0-3 before running this check."
            )

        computed = items.sum(axis=1, min_count=len(PHQ9_ITEM_NUMBERS))
        stored = df[total_col]

        comparable = computed.notna() & stored.notna()
        mismatched = comparable & (computed != stored)
        # stored value present but not reconstructable, or vice versa
        only_one_side = computed.notna() ^ stored.notna()

        rows.append(
            {
                "total_column": total_col,
                "timepoint": timepoint,
                "n_comparable": int(comparable.sum()),
                "n_mismatched": int(mismatched.sum()),
                "n_one_sided": int(only_one_side.sum()),
                "recoverable": bool(mismatched.sum() == 0 and only_one_side.sum() == 0),
            }
        )

    return pd.DataFrame(rows)


def drop_recoverable_totals(df: pd.DataFrame, report: pd.DataFrame) -> pd.DataFrame:
    """Drop every total column the check proved redundant."""
    droppable = report.loc[report["recoverable"], "total_column"].tolist()
    return df.drop(columns=droppable)


def to_long(df: pd.DataFrame, time_independent: list[str]) -> pd.DataFrame:
    """Stack the three visits, stripping the ``GI_B{t}_`` prefix from each stub."""
    time_varying = [c for c in df.columns if c not in time_independent]

    frames = []
    for timepoint, months in TIMEPOINT_TO_MONTHS.items():
        prefix = f"GI_{timepoint}_"
        visit_cols = [c for c in time_varying if c.startswith(prefix)]

        visit = df[time_independent + visit_cols].copy()
        visit.columns = [c.removeprefix("GI_B1_") for c in time_independent] + [
            c.removeprefix(prefix) for c in visit_cols
        ]
        visit.insert(len(time_independent), "follow_up_months", months)
        frames.append(visit)

    long = (
        pd.concat(frames, ignore_index=True)
        .rename(columns=ANALYSIS_NAMES, errors="raise")
        .sort_values(["patient_id", "follow_up_months"])
        .reset_index(drop=True)
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

    df = df.convert_dtypes()

    df.replace(to_replace=r"^\s*$", value=pd.NA, inplace=True, regex=True)

    # Remove rows containing only missing values.
    df.dropna(how="all", axis="index", inplace=True)

    # Remove leading and trailing whitespace from column names.
    df.columns = df.columns.str.strip()

    df = normalise_column_names(df)
    time_independent, _ = partition_columns(df)

    phq_report = check_phq_totals(df)
    df = drop_recoverable_totals(df, phq_report)

    long = to_long(df, time_independent)

    # Remove columns containing only missing values. Deliberately AFTER the
    # structural steps: an all-empty medication slot dropped up front would
    # break normalise_column_names(errors="raise") and partition_columns.
    long.dropna(how="all", axis="columns", inplace=True)

    return long
