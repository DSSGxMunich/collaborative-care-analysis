"""Cluster: use of health services during the trial.

Not a baseline risk dimension. These columns record what care a patient
actually received while the trial ran, which matters for a collaborative-care
question in two ways: it is how the control arm's usual care can be described,
and it separates patients who engaged with services from those who did not.

Everything here is **row-level**, tied to ``follow_up_months`` the way the
instrument scores are, rather than carried from baseline.

One thing is deliberately not harmonized: **counts**. ds_08 asks how many
visits during follow-up, ds_11 asks separately about the last month, the last
three months and the last six months, and ds_10 records only whether a visit
happened. A count over one month and a count over six are not the same
quantity, and the harmonized column would silently mix them. What every study
does answer is whether the service was used at all in the period it asked
about, so that is what the columns record, and the period still varies by study
and by wave. Recorded in REFERENCE_PERIODS so nobody reads them as rates.
"""

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.harmonization_column_clusters import checks
from collaborative_care_analysis.harmonization_column_clusters.concat import ID_COLS

CLUSTER_KEY = "service_use"
HARMONIZED_COLS = [
    "used_primary_care",
    "used_mental_health_service",
    "had_hospital_admission",
    "had_emergency_visit",
]

# {column: {study: [raw columns]}}. Positive when any listed column is
# positive, so a study that asks about psychologists, psychiatrists and
# counsellors separately answers one mental-health question.
SOURCES = {
    "used_primary_care": {
        "08_Coventry_2015": ["fsuq1", "fsuq2"],  # GP at surgery, GP at home
        "10_Fletcher_2021a": ["gp"],
        "11_Fletcher_2021b": ["gpvisit"],
    },
    "used_mental_health_service": {
        # counsellor, mental health worker
        "08_Coventry_2015": ["fsuq6", "fsuq7"],
        "09_Davidson_2013": ["counsel_psychi", "counsel_psycho"],
        "11_Fletcher_2021b": [
            "psychologistvisit",
            "psychiatristvisit",
            "counsellorvisit",
        ],
    },
    "had_hospital_admission": {
        "10_Fletcher_2021a": ["hospital"],
    },
    "had_emergency_visit": {
        "10_Fletcher_2021a": ["ed"],
        "11_Fletcher_2021b": ["emergencyvisit"],
    },
}

# What each study actually asked about, because the harmonized flag cannot
# carry it. ds_11's three waves ask over three different windows.
REFERENCE_PERIODS = {
    "08_Coventry_2015": "since randomisation, asked once at a single follow-up visit "
    "that ranges from 2.9 to 16.2 months",
    "09_Davidson_2013": "the six months to the month-6 visit",
    "10_Fletcher_2021a": "since the previous visit, asked at 6, 12 and 18 months",
    "11_Fletcher_2021b": "the last month at wave 1, the last three months at wave 2 and "
    "the last six months at wave 3",
}

# Values that are neither yes nor no. ds_09 uses -1 for three patients.
MISSING_CODES = {-1.0}

_YES = {"yes", "true", "1", "1.0"}
_NO = {"no", "false", "0", "0.0"}


def _used(df: pd.DataFrame, study_id: str, column: str) -> pd.Series:
    """True when the service was used at all: a yes, or a visit count above zero."""
    rows = df[COLNAME_STUDYID] == study_id
    raw = df.loc[rows, column]
    text = raw.astype("string").str.strip().str.lower()
    numeric = pd.to_numeric(raw, errors="coerce")

    used = pd.Series(pd.NA, index=raw.index, dtype="boolean")
    used.loc[text.isin(_YES)] = True
    used.loc[text.isin(_NO)] = False
    # Counts: anything above zero is use. Applied after the yes/no mapping so a
    # plain 0/1 column is read as a flag either way, which agrees.
    countable = numeric.notna() & ~numeric.isin(MISSING_CODES)
    used.loc[countable] = numeric[countable] > 0

    unusable = numeric.isin(MISSING_CODES)
    if unusable.any():
        logger.warning(
            f"{study_id} {column}: {int(unusable.sum())} row(s) carry a missing code "
            f"{sorted(MISSING_CODES)} and are left missing."
        )
        used.loc[unusable] = pd.NA
    return used


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize service use across studies, at row level."""
    harmonized_df = df[ID_COLS].copy()
    for name, per_study in SOURCES.items():
        values = pd.Series(pd.NA, index=df.index, dtype="boolean")
        for study_id, columns in per_study.items():
            checks.require_columns(df, study_id, columns, CLUSTER_KEY)
            rows = checks.require_rows(df, study_id, CLUSTER_KEY)
            answers = pd.concat([_used(df, study_id, c) for c in columns], axis=1)
            any_used = answers.fillna(False).any(axis=1)
            none_answered = answers.isna().all(axis=1)
            values.loc[rows] = any_used.astype("boolean").where(~none_answered, pd.NA)
        harmonized_df[name] = values
    return harmonized_df[ID_COLS + HARMONIZED_COLS]


COLUMN_PROVENANCE = {
    name: {
        "description": description,
        "transformation": (
            "True when the service was used at all in the period that study asked "
            "about, either a yes/no answer or a visit count above zero. Counts are "
            "deliberately not pooled: the reference periods differ by study and by "
            "wave, so a count would mix a month with six months. See reference_periods."
        ),
        "source_columns": {s: ", ".join(c) for s, c in SOURCES[name].items()},
        "reference_periods": REFERENCE_PERIODS,
    }
    for name, description in {
        "used_primary_care": "Saw a GP, at the surgery or at home.",
        "used_mental_health_service": "Saw a counsellor, psychologist, psychiatrist or "
        "mental health worker.",
        "had_hospital_admission": "Admitted to hospital.",
        "had_emergency_visit": "Attended an emergency department.",
    }.items()
}

CONSUMPTION = {
    "sources": {
        study: sorted(
            {
                c
                for name in SOURCES
                for s, cols in SOURCES[name].items()
                if s == study
                for c in cols
            }
        )
        for study in {s for name in SOURCES for s in SOURCES[name]}
    },
    "superseded": {},
    "review": {
        "fnumber1": "ds_08: visit counts. Real data, but the reference period differs "
        "from every other study's, so counts are not pooled. See REFERENCE_PERIODS.",
        "hospitalnum": "ds_10: number of hospital contacts, with values up to 120 that "
        "may be days rather than admissions. Not used until that is settled.",
        "d_12_4_outpatient": "ds_26: a 135-column service-use and costing battery, almost "
        "entirely unlabelled. Worth a pass of its own with the trial's own forms.",
        "counsel": "ds_09: an overall counselling flag that uses -1 for missing; the "
        "provider-specific columns are used instead.",
    },
    "conditional_on": {},
}
