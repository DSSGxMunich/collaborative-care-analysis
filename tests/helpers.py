import importlib
from pathlib import Path

import pandas as pd

from collaborative_care_analysis.dataset import DATA_LOADING_DIR, PACKAGE_DIR, _get_study_id

COLNAME_PATIENT_ID = "patient_id"
COLNAME_FOLLOW_UP = "follow_up_months"
PATIENT_VISIT_KEYS = ["STUDY_ID", COLNAME_PATIENT_ID, COLNAME_FOLLOW_UP]

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


def present(df: pd.DataFrame, cols: list[str]) -> list[str]:
    """Return only the columns from `cols` that actually exist in `df`.

    Several instrument checks are written against a fixed item list (e.g.
    all 9 PHQ-9 items), but not every dataset variant carries every
    instrument -- this lets a test degrade to 'skip' instead of KeyError
    when a study simply doesn't have that scale.
    """
    return [c for c in cols if c in df.columns]


def assert_in_range(series: pd.Series, low: float, high: float, label: str) -> None:
    """Assert every non-null value in `series` falls within [low, high].

    Used for instrument total/item scores, where an out-of-range value
    almost always means a scoring or harmonization bug rather than a real
    response (e.g. a PHQ-9 item of 5 when the scale tops out at 3).
    """
    valid = series.dropna()
    out_of_range = valid[(valid < low) | (valid > high)]
    assert out_of_range.empty, (
        f"{label}: {len(out_of_range)} value(s) outside [{low}, {high}]: "
        f"{sorted(out_of_range.unique())[:10]}"
    )


def find_non_integer_rows(df: pd.DataFrame, cols: list[str], id_cols: list[str]) -> pd.DataFrame:
    """Return one row per (id_cols, offending column, value) for every value
    in `cols` that isn't integer-valued (e.g. 3.5 instead of 3 or 4).

    Item/total scores that are counts should never hold a fraction -- this
    shows up when an averaging or rescaling step runs where a sum should
    have, or a unit conversion gets applied to a count field by mistake.
    `id_cols` (typically study id + patient id) are carried along so a
    failure points straight at the source row instead of just a column name.
    Values are compared via `dtype`, not `%1 != 0`, so pandas' nullable NA
    values never raise or get miscounted.
    """
    bad_frames = []
    for col in cols:
        valid = df[col].dropna()
        non_integer = valid[valid.astype(float) % 1 != 0]
        if not non_integer.empty:
            frame = df.loc[non_integer.index, id_cols].copy()
            frame["column"] = col
            frame["value"] = non_integer.to_numpy()
            bad_frames.append(frame)

    if not bad_frames:
        return pd.DataFrame(columns=id_cols + ["column", "value"])
    return pd.concat(bad_frames, ignore_index=True)


# Loader-discovery helpers


def loader_scripts() -> list[Path]:
    """Every per-study data-loading script, for use in @pytest.mark.parametrize."""
    return [p for p in sorted(DATA_LOADING_DIR.rglob("*.py")) if p.name != "__init__.py"]


def import_loader(script_path: Path):
    """Import a loader script as a module, given its path on disk."""
    module_path = ".".join(
        (
            "collaborative_care_analysis",
            *script_path.relative_to(PACKAGE_DIR).with_suffix("").parts,
        )
    )
    return importlib.import_module(module_path)


def loader_study_ids() -> set[str]:
    """STUDY_ID of every data-loading script (e.g. '16_Katon_1999')."""
    return {
        _get_study_id(path)
        for path in DATA_LOADING_DIR.rglob("*.py")
        if path.name != "__init__.py"
    }
