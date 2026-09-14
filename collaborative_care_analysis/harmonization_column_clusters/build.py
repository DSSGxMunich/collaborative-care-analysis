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
from collaborative_care_analysis.harmonization_column_clusters import checks, registry
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


def _final_audit(built: pd.DataFrame, column_mapping: dict) -> None:
    """Log what the assembled frame looks like, and flag anything unusable.

    Run once at the end, because some problems only exist across clusters: a
    column no study populates, a column only one study populates, or a study
    that came out of the whole process with nothing at all.
    """
    harmonized = [c for c in built.columns if c not in ID_COLS]
    logger.info(f"Built {len(harmonized)} harmonized column(s) over {len(built)} rows.")

    for column in harmonized:
        if built[column].notna().sum() == 0:
            raise ValueError(
                f"{column!r} is empty for every row in every study. A harmonized column "
                f"that nothing populates is a broken mapping, not a sparse one."
            )

    single = [
        column
        for column in harmonized
        if built.loc[built[column].notna(), COLNAME_STUDYID].nunique() == 1
    ]
    if single:
        logger.info(
            f"{len(single)} column(s) come from a single study and carry only "
            f"within-study information: {single}."
        )

    contributing = {
        study
        for column in harmonized
        for study in built.loc[built[column].notna(), COLNAME_STUDYID].unique()
    }
    if barren := sorted(set(built[COLNAME_STUDYID].unique()) - contributing):
        logger.warning(
            f"{len(barren)} study(ies) contribute to no harmonized column at all: {barren}."
        )

    per_study = built[harmonized].notna().groupby(built[COLNAME_STUDYID]).any().sum(axis=1)
    logger.info(
        f"Columns answered per study: median {int(per_study.median())}, "
        f"range {int(per_study.min())} ({per_study.idxmin()}) to "
        f"{int(per_study.max())} ({per_study.idxmax()})."
    )


def load_harmonized() -> pd.DataFrame:
    """Read the harmonized frame back with its dtypes intact.

    ``pd.read_csv`` on its own re-infers types per chunk, which turns every
    nullable boolean into ``object`` and warns about mixed types. That loses
    the three-valued distinction the clusters exist to preserve: ``False``
    (the study asked and the answer was no) and ``pd.NA`` (the study never
    asked) both become indistinguishable truthy objects.

    Use this instead of reading the CSV directly.
    """
    frame_path = OUTPUT_DIR / "harmonized_data.csv"
    dtypes_path = OUTPUT_DIR / "dtypes.json"
    for path in (frame_path, dtypes_path):
        if not path.exists():
            raise FileNotFoundError(
                f"{path.name} not found in {OUTPUT_DIR}. Run "
                "'uv run collaborative_care_analysis/dataset.py ai-run' to build it."
            )
    dtypes = json.loads(dtypes_path.read_text())
    return pd.read_csv(frame_path, dtype=dtypes)


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
        for study_id, column in registry.source_pairs(module.CONSUMPTION):
            if column in raw_df.columns:
                checks.check_magnitude(
                    raw_df.loc[raw_df[COLNAME_STUDYID] == study_id, column],
                    cluster_key,
                    study_id,
                    column,
                )
        cluster_df = module.harmonize(raw_df)

        if list(cluster_df.columns[: len(ID_COLS)]) != ID_COLS:
            raise ValueError(f"{cluster_key}: cluster output must start with {ID_COLS}")
        if len(cluster_df) != len(raw_df):
            raise ValueError(
                f"{cluster_key}: cluster changed the row count "
                f"({len(cluster_df)} vs {len(raw_df)}); it must stay row-aligned"
            )

        emitted = list(cluster_df.columns[len(ID_COLS) :])
        if declared := [c for c in module.HARMONIZED_COLS if c not in emitted]:
            raise ValueError(
                f"{cluster_key}: HARMONIZED_COLS promises {declared} but harmonize() did "
                f"not return them; the module's contract and its code disagree."
            )
        if undeclared := [c for c in emitted if c not in module.HARMONIZED_COLS]:
            raise ValueError(
                f"{cluster_key}: harmonize() returned {undeclared}, which HARMONIZED_COLS "
                f"does not declare, so nothing downstream knows they exist."
            )
        if clash := [c for c in emitted if c in built.columns]:
            raise ValueError(
                f"{cluster_key}: would overwrite {clash}, already produced by another "
                f"cluster. Two clusters must not claim the same column name."
            )
        if missing_provenance := [c for c in emitted if c not in provenance]:
            raise ValueError(
                f"{cluster_key}: {missing_provenance} have no COLUMN_PROVENANCE entry, so "
                f"column_mapping.json would not say where they came from."
            )

        for column in emitted:
            # .array, not .to_numpy(): to_numpy() on a nullable boolean/Int64
            # column returns an object array and silently drops the dtype. The
            # row-count check above already guarantees positional alignment.
            built[column] = pd.Series(cluster_df[column].array, index=built.index)
            column_mapping[column] = {
                "cluster": cluster_key,
                **provenance[column],
                **_coverage_by_study(built, column),
            }
        checks.summarize(raw_df, cluster_df, cluster_key)
        logger.success(f"Cluster '{cluster_key}': added {emitted}")

    _final_audit(built, column_mapping)

    built.to_csv(OUTPUT_DIR / "harmonized_data.csv", index=False)
    (OUTPUT_DIR / "column_mapping.json").write_text(json.dumps(column_mapping, indent=2) + "\n")
    # CSV carries no dtypes, so a plain read_csv infers per chunk and warns about
    # mixed types on every nullable boolean. Ship the dtypes alongside so readers
    # can restore them: pd.read_csv(path, dtype=json.load(open(dtypes.json))).
    dtypes = {column: str(dtype) for column, dtype in built.dtypes.items()}
    (OUTPUT_DIR / "dtypes.json").write_text(json.dumps(dtypes, indent=2) + "\n")
    logger.success(
        f"Wrote harmonized_data.csv ({built.shape}), column_mapping.json and dtypes.json."
    )

    record_unclustered(raw_df)

    return built
