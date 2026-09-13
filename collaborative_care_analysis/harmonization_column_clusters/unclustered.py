"""Record which raw columns the implemented clusters have and have not touched.

The harmonized build keeps every raw column, so the working frame stays the
system of record. This module makes the two halves of it addressable:

* ``touched_columns`` -- raw columns some cluster actually read, superseded or
  deliberately retained for review. Subsetting to these gives you the part of
  the frame the harmonization steps have inspected.
* ``unclustered`` -- everything else, keyed ``<study_id>::<column>`` so a name
  reused across studies with different meanings stays distinguishable (the
  same convention ``dropped_columns.json`` uses).

IMPORTANT -- what "unclustered" means right now. With only some of the 19
target clusters implemented, the overwhelming majority of entries are
unclustered because **no cluster has reached them yet**, not because they were
examined and judged not to fit a risk dimension. Each entry therefore carries a
``status`` saying which of the two it is, and no triage reason is invented for
columns nobody has looked at. As clusters are added, entries move from
``not_yet_reviewed`` to either touched or an explicit ``does_not_fit`` with a
reason, so the file is a live work queue rather than a verdict.
"""

import json

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID, INTERIM_DATA_DIR
from collaborative_care_analysis.harmonization_column_clusters.concat import ID_COLS
from collaborative_care_analysis.harmonization_column_clusters.registry import cluster_modules
from collaborative_care_analysis.harmonization_column_clusters.variable_labels import (
    describe_column,
)

OUTPUT_DIR = INTERIM_DATA_DIR / "column_clusters_harmonized"
UNCLUSTERED_COLUMNS_PATH = OUTPUT_DIR / "unclustered_columns.json"

# Columns judged, by a human, not to belong to any of the 19 target dimensions.
# Keyed <study_id>::<column> or a bare column name to cover every study holding
# it. Kept here rather than in the generated file so the reasoning is reviewable
# in the diff, and so regenerating never overwrites it.
DOES_NOT_FIT: dict[str, str] = {}


def touched_by_cluster() -> dict[str, set[str]]:
    """Raw column names each implemented cluster reads, supersedes or reviews."""
    touched = {}
    for module in cluster_modules():
        consumption = module.CONSUMPTION
        columns: set[str] = set()
        for key in ("sources", "fallback_sources"):
            columns.update(consumption.get(key, {}).values())
        for key in ("superseded", "review", "conditional_on"):
            columns.update(consumption.get(key, {}))
        touched[module.CLUSTER_KEY] = columns
    return touched


def all_touched_columns() -> set[str]:
    """Every raw column any implemented cluster has inspected."""
    return set().union(*touched_by_cluster().values())


def collect_unclustered(raw_df: pd.DataFrame) -> pd.DataFrame:
    """One row per (study, column) that no implemented cluster has touched."""
    touched = all_touched_columns()
    candidates = [c for c in raw_df.columns if c not in ID_COLS and c not in touched]

    rows = []
    for study_id, study_frame in raw_df.groupby(COLNAME_STUDYID, sort=True):
        present = study_frame[candidates].notna().any()
        for column in present[present].index:
            values = study_frame[column]
            rows.append(
                {
                    "study_id": study_id,
                    "column": column,
                    "dtype": str(values.dtype),
                    "pct_non_null": round(100 * values.notna().mean(), 1),
                    "original_label": describe_column(study_id, column),
                }
            )
    return pd.DataFrame(rows)


def record_unclustered(raw_df: pd.DataFrame) -> dict:
    """Write ``unclustered_columns.json`` and return what was written."""
    manifest = collect_unclustered(raw_df)
    touched_map = touched_by_cluster()
    touched = sorted(all_touched_columns() & set(raw_df.columns))

    entries = {}
    for _, row in manifest.iterrows():
        key = f"{row['study_id']}::{row['column']}"
        reason = DOES_NOT_FIT.get(key) or DOES_NOT_FIT.get(row["column"])
        entries[key] = {
            "study_id": row["study_id"],
            "column": row["column"],
            "dtype": row["dtype"],
            "pct_non_null": row["pct_non_null"],
            "original_label": row["original_label"],
            "status": "does_not_fit" if reason else "not_yet_reviewed",
            "reason": reason or "",
        }

    payload = {
        "clusters_implemented": sorted(touched_map),
        "clusters_target_total": 19,
        "touched_columns": touched,
        "counts": {
            "raw_columns": int(raw_df.shape[1] - len(ID_COLS)),
            "touched_columns": len(touched),
            "unclustered_study_column_pairs": len(entries),
            "unclustered_distinct_columns": int(manifest["column"].nunique())
            if len(manifest)
            else 0,
            "does_not_fit": sum(1 for e in entries.values() if e["status"] == "does_not_fit"),
        },
        "unclustered": entries,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    UNCLUSTERED_COLUMNS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    logger.info(
        f"Wrote unclustered_columns.json: {len(touched)} touched column(s), "
        f"{len(entries)} untouched (study, column) pair(s) across "
        f"{payload['counts']['unclustered_distinct_columns']} distinct columns."
    )
    return payload
