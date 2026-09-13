"""Track which raw columns each harmonized cluster supersedes.

Once a cluster is implemented, the raw columns it consumed no longer need to
travel in the working frame. This module answers, per cluster:

* which raw columns would be dropped, **in which study**, and what each
  originally meant (from that study's codebook, not from a guess);
* which age-adjacent columns are deliberately **kept** for review instead;
* and it records the decision to ``dropped_columns.json``, keyed
  ``<study_id>::<column>`` so a name reused across studies with different
  meanings stays distinguishable -- the same convention
  ``unclustered_columns.json`` uses.

Nothing is dropped implicitly: ``preview_drops()`` is a pure report, and
``record_drops()`` writes the manifest only when called.
"""

import json

import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID, INTERIM_DATA_DIR
from collaborative_care_analysis.harmonization_column_clusters.registry import cluster_modules
from collaborative_care_analysis.harmonization_column_clusters.variable_labels import (
    describe_column,
)

OUTPUT_DIR = INTERIM_DATA_DIR / "column_clusters_harmonized"
DROPPED_COLUMNS_PATH = OUTPUT_DIR / "dropped_columns.json"

# Each cluster module declares its own CONSUMPTION, so one cluster stays one
# file; this is just the lookup.
#   sources     -- {study_id: column} actually read to build the harmonized value
#   superseded  -- {column: reason} whose information the harmonized column now carries
#   review      -- {column: reason} never dropped automatically
#   conditional_on -- {column: harmonized column that must cover it before dropping}
CLUSTER_CONSUMPTION = {module.CLUSTER_KEY: module.CONSUMPTION for module in cluster_modules()}


def _conditional_violations(
    raw_df: pd.DataFrame, harmonized_df: pd.DataFrame, cluster_key: str
) -> dict[tuple[str, str], int]:
    """Find (study, column) pairs where dropping would lose the last route to a value.

    Implements the rule "drop the birth date where age at baseline is present":
    a conditional column may only be dropped for a study in which every patient
    holding it already has the harmonized value. Anything else is reported so it
    can be retained rather than silently discarded.
    """
    conditions = CLUSTER_CONSUMPTION[cluster_key].get("conditional_on", {})
    violations = {}
    for column, required_column in conditions.items():
        if column not in raw_df.columns:
            continue
        uncovered = raw_df[column].notna() & harmonized_df[required_column].isna()
        if not uncovered.any():
            continue
        for study_id, count in (
            raw_df.loc[uncovered].groupby(COLNAME_STUDYID)["patient_id"].nunique().items()
        ):
            violations[(study_id, column)] = int(count)
    return violations


def _studies_holding(df: pd.DataFrame, column: str) -> list[str]:
    """Studies where this column exists with at least one non-null value."""
    if column not in df.columns:
        return []
    holders = df.loc[df[column].notna(), COLNAME_STUDYID].unique()
    return sorted(holders)


def collect_drops(
    df: pd.DataFrame, cluster_key: str, harmonized_df: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Build the per-(study, column) drop manifest for one cluster.

    Includes a safety check: a column is only safe to drop if every study
    holding it is a study this cluster actually accounted for. Anything else is
    flagged ``UNACCOUNTED`` rather than silently dropped, since raw column names
    are reused across studies for unrelated constructs.
    """
    consumption = CLUSTER_CONSUMPTION[cluster_key]
    # "sources" (always consumed) and "fallback_sources" (consumed only where the
    # primary source is missing/implausible) are both real {study_id: column}
    # maps. A study can appear in both under DIFFERENT columns (e.g. ds_11's
    # primary age source is "AGE", its fallback is "age_0"), so the per-column
    # study-sets are unioned rather than the dicts merged by key.
    primary = consumption["sources"]
    fallback = consumption.get("fallback_sources", {})
    source_columns = set(primary.values()) | set(fallback.values())
    accounted_studies = {
        column: {sid for sid, col in primary.items() if col == column}
        | {sid for sid, col in fallback.items() if col == column}
        for column in source_columns
    }

    # A column can appear in more than one bucket -- e.g. ds_12's `gebdatum` is
    # both the input to its derived age and a birth date needing a conscious
    # keep/drop decision. `review` wins, so nothing flagged for review can be
    # dropped by virtue of also being a source.
    dispositions = {}
    reasons = {}
    for column in sorted(source_columns):
        dispositions[column] = "source"
        reasons[column] = "consumed as the harmonized value's source"
    for column, reason in consumption["superseded"].items():
        dispositions[column] = "superseded"
        reasons[column] = reason
    for column, reason in consumption["review"].items():
        dispositions[column] = "review"
        reasons[column] = reason

    violations = (
        _conditional_violations(df, harmonized_df, cluster_key)
        if harmonized_df is not None
        else {}
    )

    records = []
    for column, column_disposition in dispositions.items():
        for study_id in _studies_holding(df, column):
            # Per-study locals: a retention in one study must not leak to the next.
            disposition = column_disposition
            reason = reasons[column]

            if disposition == "source" and study_id not in accounted_studies.get(column, set()):
                disposition = "UNACCOUNTED"

            uncovered_patients = violations.get((study_id, column))
            if uncovered_patients:
                disposition = "review"
                reason = (
                    f"{reason} RETAINED: {uncovered_patients} patient(s) hold this column but "
                    f"have no {CLUSTER_CONSUMPTION[cluster_key]['conditional_on'][column]}, so "
                    "dropping it would remove the last route to their value."
                )

            records.append(
                {
                    "study_id": study_id,
                    "column": column,
                    "disposition": disposition,
                    "original_label": describe_column(study_id, column),
                    "pct_non_null": round(
                        df.loc[df[COLNAME_STUDYID] == study_id, column].notna().mean() * 100, 1
                    ),
                    "reason": reason,
                }
            )

    return pd.DataFrame(records).sort_values(["disposition", "column", "study_id"])


def preview_drops(
    df: pd.DataFrame, cluster_key: str, harmonized_df: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Print, and return, what dropping this cluster's raw columns would do."""
    manifest = collect_drops(df, cluster_key, harmonized_df)
    for disposition, group in manifest.groupby("disposition"):
        verb = {
            "source": "WOULD DROP (consumed as source)",
            "superseded": "WOULD DROP (superseded)",
            "review": "KEPT -- needs a decision",
            "UNACCOUNTED": "!! NOT SAFE TO DROP -- study not accounted for by this cluster",
        }[disposition]
        print(f"\n=== {verb}: {len(group)} (study, column) pairs ===")
        for _, row in group.iterrows():
            print(
                f"  {row['study_id']:<20} {row['column']:<18} "
                f"{row['pct_non_null']:>5.1f}%  {row['original_label'][:56]}"
            )
    return manifest


def apply_drops(
    df: pd.DataFrame, cluster_key: str, harmonized_df: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Return ``df`` without the columns this cluster supersedes.

    Only ``source`` and ``superseded`` columns are removed; ``review`` columns
    and anything flagged ``UNACCOUNTED`` are left in place.
    """
    manifest = collect_drops(df, cluster_key, harmonized_df)
    droppable = manifest.loc[manifest["disposition"].isin(["source", "superseded"]), "column"]
    return df.drop(columns=sorted(set(droppable) & set(df.columns)))


def record_drops(
    df: pd.DataFrame,
    cluster_key: str,
    harmonized_columns: list[str],
    harmonized_df: pd.DataFrame | None = None,
) -> dict:
    """Append this cluster's drop manifest to ``dropped_columns.json``.

    Keyed by cluster ("per step"), then by ``<study_id>::<column>`` so each
    dropped column is always attributable to the study it came from.
    """
    manifest = collect_drops(df, cluster_key, harmonized_df)
    existing = (
        json.loads(DROPPED_COLUMNS_PATH.read_text()) if DROPPED_COLUMNS_PATH.exists() else {}
    )

    def entries(disposition_values: list[str]) -> dict:
        rows = manifest[manifest["disposition"].isin(disposition_values)]
        return {
            f"{row['study_id']}::{row['column']}": {
                "study_id": row["study_id"],
                "column": row["column"],
                "original_label": row["original_label"],
                "disposition": row["disposition"],
                "pct_non_null": row["pct_non_null"],
                "reason": row["reason"],
            }
            for _, row in rows.iterrows()
        }

    existing[cluster_key] = {
        "harmonized_columns": harmonized_columns,
        "dropped": entries(["source", "superseded"]),
        "retained_for_review": entries(["review"]),
        "not_safe_to_drop": entries(["UNACCOUNTED"]),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DROPPED_COLUMNS_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n")
    return existing[cluster_key]
