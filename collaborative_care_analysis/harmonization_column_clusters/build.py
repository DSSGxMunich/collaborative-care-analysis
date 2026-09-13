"""Build the column-cluster harmonized dataset (Step 5 of PROMPT_column_harmonization.md).

Applies every *implemented* cluster module to the concatenated raw exports and
writes ``harmonized_data.csv`` plus ``column_mapping.json`` into
``data/interim/column_clusters_harmonized/``.

Clusters are added to ``IMPLEMENTED_CLUSTERS`` only once their design has been
approved at the Step 3 checkpoint, so re-running this rebuilds exactly the
approved set and nothing else. ``column_mapping.json``'s per-study coverage is
recomputed from the built data rather than hand-maintained, so it cannot drift
out of date relative to ``harmonized_data.csv``.

Usage::

    uv run python -c "from collaborative_care_analysis.harmonization_column_clusters.build \\
        import build; build()"
"""

import json

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID, INTERIM_DATA_DIR
from collaborative_care_analysis.harmonization_column_clusters.concat import (
    ID_COLS,
    load_concatenated_raw,
)
from collaborative_care_analysis.harmonization_column_clusters.registry import cluster_modules
from collaborative_care_analysis.harmonization_column_clusters.unclustered import (
    record_unclustered,
)

OUTPUT_DIR = INTERIM_DATA_DIR / "column_clusters_harmonized"

# One module per cluster, each self-contained: it defines its own CLUSTER_KEY,
# HARMONIZED_COLS, harmonize(), COLUMN_PROVENANCE and CONSUMPTION. Which ones
# are built is decided by registry.IMPLEMENTED_CLUSTERS, so nothing
# cluster-specific belongs in this file.


def _coverage_by_study(built: pd.DataFrame, column: str) -> dict:
    """Return which studies have the column populated, and how densely."""
    counts = built.groupby(COLNAME_STUDYID)[column].agg(["count", "size"])
    non_null_by_study, rows_by_study = counts["count"], counts["size"]

    contributing = sorted(non_null_by_study[non_null_by_study > 0].index)
    return {
        "studies_contributing": contributing,
        "studies_missing": sorted(non_null_by_study[non_null_by_study == 0].index),
        "pct_non_missing_overall": round(built[column].notna().mean() * 100, 2),
        "pct_non_missing_by_study": {
            study_id: round(non_null_by_study[study_id] / rows_by_study[study_id] * 100, 2)
            for study_id in contributing
        },
    }


def build() -> pd.DataFrame:
    """Apply every implemented cluster and write the harmonized outputs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = load_concatenated_raw()
    logger.info(f"Concatenated {raw_df[COLNAME_STUDYID].nunique()} studies, {len(raw_df)} rows.")

    built = raw_df[ID_COLS].copy()
    column_mapping = {}

    for module in cluster_modules():
        cluster_key = module.CLUSTER_KEY
        provenance = module.COLUMN_PROVENANCE
        cluster_df = module.harmonize(raw_df)

        if list(cluster_df.columns[: len(ID_COLS)]) != ID_COLS:
            raise ValueError(f"{cluster_key}: cluster output must start with {ID_COLS}")
        if len(cluster_df) != len(raw_df):
            raise ValueError(
                f"{cluster_key}: cluster changed the row count "
                f"({len(cluster_df)} vs {len(raw_df)}); it must stay row-aligned"
            )

        for column in cluster_df.columns[len(ID_COLS) :]:
            built[column] = cluster_df[column].to_numpy()
            column_mapping[column] = {
                "cluster": cluster_key,
                **provenance[column],
                **_coverage_by_study(built, column),
            }
        logger.success(
            f"Cluster '{cluster_key}': added {list(cluster_df.columns[len(ID_COLS) :])}"
        )

    built.to_csv(OUTPUT_DIR / "harmonized_data.csv", index=False)
    (OUTPUT_DIR / "column_mapping.json").write_text(json.dumps(column_mapping, indent=2) + "\n")
    logger.success(f"Wrote harmonized_data.csv ({built.shape}) and column_mapping.json.")

    record_unclustered(raw_df)

    return built
