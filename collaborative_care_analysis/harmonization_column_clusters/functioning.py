"""Cluster: Iezzoni dimensions 7 and 10 -- physical function, health and quality of life.

Two instruments carry this across studies, and they need opposite treatment.

**SF-12 / SF-36 summary scores pool directly.** The physical and mental
component summaries are norm-based T-scores, standardised to a mean of 50 and
a standard deviation of 10 in a reference population, precisely so that they
can be compared between samples and between the 12- and 36-item versions. The
three studies here sit where a depressed cohort should: physical means of 44
to 50, mental means of 39 to 40.

**EQ-5D levels do not pool directly.** ds_13 and ds_21 used the three-level
version, where each dimension runs 1 to 3. ds_04 and ds_08 used the five-level
version, running 1 to 5. A "3" means "extreme problems" in one and "moderate
problems" in the other, so averaging or pooling the raw levels would be a scale
error of exactly the kind this package exists to prevent.

What both versions agree on is level 1: no problems. So the harmonized columns
are per-dimension *any problem* flags, which are identical in meaning across
versions, rather than a level that is not. The severity ordering within each
version is lost, deliberately, in exchange for four studies that can be
compared instead of two pairs that cannot.

ds_12's ``eq5d10``..``eq5d50`` hold only 0 and 1 rather than EQ-5D levels, so
they are not the instrument's dimensions and are left alone.
"""

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.harmonization_column_clusters import checks
from collaborative_care_analysis.harmonization_column_clusters.concat import ID_COLS

CLUSTER_KEY = "functioning"

EQ5D_DIMENSIONS = [
    "eq5d_mobility_problem",
    "eq5d_self_care_problem",
    "eq5d_usual_activities_problem",
    "eq5d_pain_problem",
    "eq5d_anxiety_depression_problem",
]
HARMONIZED_COLS = [
    "sf_physical_component",
    "sf_mental_component",
    *EQ5D_DIMENSIONS,
    "eq5d_vas",
]

# Per study, the five EQ-5D dimension columns in the canonical order
# (mobility, self-care, usual activities, pain, anxiety/depression), with the
# version so the level ceiling is checked rather than assumed.
EQ5D_SOURCES = {
    # Two-letter names, decoded from this study's Stata codebook log:
    # mo Mobility, sc Self-care, ua Usual activities, pd Pain/Discomfort,
    # ad Anxiety/Depression, all EQ-5D-5L. "ad" is anxiety and depression, not
    # antidepressant, which is exactly what it looks like at a glance.
    "10_Fletcher_2021a": (["mo", "sc", "ua", "pd", "ad"], 5),
    "04_Bekelman_2018": (["eq5d01", "eq5d02", "eq5d03", "eq5d04", "eq5d05"], 5),
    "08_Coventry_2015": (["eq5d1", "eq5d2", "eq5d3", "eq5d4", "eq5d5"], 5),
    "13_Hölzel_2018": (
        [
            "EQ5D_Beweglichkeit",
            "EQ5D_Selbstversorgung",
            "EQ5D_AllgTaetigkeiten",
            "EQ5D_Schmerzen",
            "EQ5D_Angst_Depression",
        ],
        3,
    ),
    "21_Richards_2008": (
        [
            "eq5d_mobility",
            "eq5d_self_care",
            "eq5d_usual_activities",
            "eq5d_pain",
            "eq5d_mood",
        ],
        3,
    ),
}

# Norm-based summary scores. Plausible range for a T-score, generously bounded:
# anything outside it is a coding error rather than a real score.
SF_SOURCES = {
    "sf_physical_component": {
        "24_Rollman_2016": "pcs",
        "25_Rollman_2017": "PCS",
        "32_Wells_2000": "PCS12",
    },
    "sf_mental_component": {
        "24_Rollman_2016": "mcs",
        "25_Rollman_2017": "MCS",
        "32_Wells_2000": "MCS12",
    },
}
SF_PLAUSIBLE_RANGE = (-10.0, 100.0)

# The EQ-5D visual analogue scale: "your health today" marked on a 0 to 100
# line. Same instrument and same range in all three, and unlike the utility
# index it needs no national value set, so it pools directly.
VAS_SOURCES = {
    "10_Fletcher_2021a": "eq_vas",
    "12_Gensichen_2009": "GHZ_T2",  # "Heutiger Gesundheitszustand (Skala)"
    "13_Hölzel_2018": "EQ5D_Gesundheitszustand",
}
VAS_RANGE = (0.0, 100.0)

NOT_POOLED = {
    "eq5d_index": "ds_10, ds_21 and ds_22 carry an EQ-5D utility index, but a utility is "
    "produced by applying a national value set to the levels, and the three studies are "
    "in different countries. Two indices on different tariffs are not the same quantity.",
    "kccq": "ds_04 and ds_05 only, and specific to heart failure, so it describes a "
    "different construct from a general quality-of-life score.",
}


def _eq5d_problem(df: pd.DataFrame, study_id: str, column: str, ceiling: int) -> pd.Series:
    """True when the patient reports any problem on one EQ-5D dimension.

    Level 1 is "no problems" in both the three- and five-level versions, which
    is what makes this comparable where the raw level is not.
    """
    rows = df[COLNAME_STUDYID] == study_id
    values = pd.to_numeric(df.loc[rows, column], errors="coerce")
    outside = values.notna() & ~values.between(1, ceiling)
    if outside.any():
        logger.warning(
            f"{study_id} {column}: {int(outside.sum())} value(s) outside 1-{ceiling}, the "
            "range of this EQ-5D version, set to missing."
        )
    values = values.where(~outside)
    return (values > 1).astype("boolean").where(values.notna())


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize the functioning and quality-of-life cluster."""
    harmonized_df = df[ID_COLS].copy()

    for position, name in enumerate(EQ5D_DIMENSIONS):
        values = pd.Series(pd.NA, index=df.index, dtype="boolean")
        for study_id, (columns, ceiling) in EQ5D_SOURCES.items():
            column = columns[position]
            checks.require_columns(df, study_id, [column], CLUSTER_KEY)
            rows = checks.require_rows(df, study_id, CLUSTER_KEY)
            values.loc[rows] = _eq5d_problem(df, study_id, column, ceiling)
        harmonized_df[name] = values

    for name, per_study in SF_SOURCES.items():
        values = pd.Series(pd.NA, index=df.index, dtype="Float64")
        for study_id, column in per_study.items():
            checks.require_columns(df, study_id, [column], CLUSTER_KEY)
            rows = checks.require_rows(df, study_id, CLUSTER_KEY)
            score = pd.to_numeric(df.loc[rows, column], errors="coerce")
            outside = score.notna() & ~score.between(*SF_PLAUSIBLE_RANGE)
            if outside.any():
                logger.warning(
                    f"{study_id} {column}: {int(outside.sum())} score(s) outside "
                    f"{SF_PLAUSIBLE_RANGE} set to missing."
                )
            values.loc[rows] = score.where(~outside).astype("Float64")
        harmonized_df[name] = values

    vas = pd.Series(pd.NA, index=df.index, dtype="Float64")
    for study_id, column in VAS_SOURCES.items():
        checks.require_columns(df, study_id, [column], CLUSTER_KEY)
        rows = checks.require_rows(df, study_id, CLUSTER_KEY)
        score = pd.to_numeric(df.loc[rows, column], errors="coerce")
        outside = score.notna() & ~score.between(*VAS_RANGE)
        if outside.any():
            logger.warning(
                f"{study_id} {column}: {int(outside.sum())} VAS value(s) outside "
                f"{VAS_RANGE} set to missing."
            )
        vas.loc[rows] = score.where(~outside).astype("Float64")
    harmonized_df["eq5d_vas"] = vas

    return harmonized_df[ID_COLS + HARMONIZED_COLS]


_EQ5D_TRANSFORM = (
    "Recorded as any problem versus no problem on that dimension. The three- and "
    "five-level EQ-5D versions share only the meaning of level 1, so a flag is "
    "comparable across them where a level is not. Levels outside the version's own "
    "range are set missing."
)

COLUMN_PROVENANCE = {
    name: {
        "description": f"Any reported problem on the EQ-5D {label} dimension.",
        "transformation": _EQ5D_TRANSFORM,
        "source_columns": {
            study: columns[position] for study, (columns, _) in EQ5D_SOURCES.items()
        },
        "instrument_version": {
            study: f"EQ-5D-{ceiling}L" for study, (_, ceiling) in EQ5D_SOURCES.items()
        },
    }
    for position, (name, label) in enumerate(
        zip(
            EQ5D_DIMENSIONS,
            ["mobility", "self-care", "usual activities", "pain", "anxiety and depression"],
            strict=True,
        )
    )
}
COLUMN_PROVENANCE.update(
    {
        name: {
            "description": (
                f"SF-12/SF-36 {'physical' if 'physical' in name else 'mental'} component "
                "summary, a norm-based T-score with population mean 50 and SD 10."
            ),
            "transformation": (
                "Taken as scored by the study. The summaries are normed precisely so that "
                "the 12- and 36-item versions are comparable, so no rescaling is applied. "
                "Scores outside a generous plausible range are set missing."
            ),
            "source_columns": per_study,
            "not_pooled": NOT_POOLED,
        }
        for name, per_study in SF_SOURCES.items()
    }
)


COLUMN_PROVENANCE["eq5d_vas"] = {
    "description": "EQ-5D visual analogue scale, self-rated health today, 0 to 100.",
    "transformation": (
        "Taken as recorded. The VAS is the same 0-100 line in every version of the "
        "instrument and needs no national value set, so unlike the utility index it is "
        "comparable across studies."
    ),
    "source_columns": VAS_SOURCES,
}


def _sources_by_study() -> dict[str, list[str]]:
    sources: dict[str, list[str]] = {}
    for study, column in VAS_SOURCES.items():
        sources.setdefault(study, []).append(column)
    for study, (columns, _) in EQ5D_SOURCES.items():
        sources.setdefault(study, []).extend(columns)
    for per_study in SF_SOURCES.values():
        for study, column in per_study.items():
            sources.setdefault(study, []).append(column)
    return {study: sorted(set(columns)) for study, columns in sources.items()}


CONSUMPTION = {
    "sources": _sources_by_study(),
    "superseded": {},
    "review": {
        "eq5d5lscore": "ds_10: an EQ-5D utility index on a national value set. See NOT_POOLED.",
        "eq5d_total": "ds_22: same, on a different country's value set.",
        "eq5d_value": "ds_21: same.",
        "eq5d10": "ds_12: holds 0/1, not EQ-5D levels, so these are not the instrument's "
        "five dimensions despite the name.",
        "kccq01a": "ds_04, ds_05: heart-failure specific quality of life. See NOT_POOLED.",
    },
    "conditional_on": {},
}
