"""Cluster: deaths and other events that end a patient's observed trajectory.

These are not baseline risk factors and not outcome scores. They decide
whether a later measurement is missing for an ignorable reason or a
clinically informative one, which is exactly what a model of change over time
has to know.

**Read the coverage before using any of this.** Death is recorded in two
studies of thirty, withdrawal in one, cardiac events in one. For the other
twenty-eight studies a missing follow-up cannot be distinguished from a death,
so informative censoring and competing risks remain out of reach from the IPD
as delivered. The columns are built because the information that does exist
should not be thrown away, not because the cluster is fit for pooling.

Two false leads were removed on the way, both of which look like death data:

* ds_11's ``death_t`` and ``phq2wk_dead_di_t`` are labelled "Thought-of-death"
  and "Thoughts that you would be better off dead". They are suicidal-ideation
  items, in other words PHQ-9 question 9, not vital status.
* ds_32's ``cesd_item_thought_about_death`` is the same thing in the CES-D.

ds_04's death count is confirmed against its publication: the paper reports
"10 patients died receiving CASA, and 13 patients died receiving usual care",
and ``days_until_death`` is recorded for exactly those 23 patients.
"""

import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.harmonization_column_clusters import checks
from collaborative_care_analysis.harmonization_column_clusters.concat import ID_COLS

CLUSTER_KEY = "clinical_events"
HARMONIZED_COLS = [
    "died_during_follow_up",
    "days_observed",
    "withdrew_from_study",
    "had_major_adverse_cardiac_event",
]

# ds_04 stores survival the standard way: time to death for those who died,
# time to censoring for everyone still under observation. Both are recorded
# for the 23 who died, and the death is never later than the censoring, so
# the death time is the end of observation for them.
SURVIVAL_STUDY = "04_Bekelman_2018"
DAYS_UNTIL_DEATH = "days_until_death"
DAYS_UNTIL_CENSORING = "days_until_censoring"

# ds_09 records adjudicated events as yes/no over the whole follow-up.
EVENT_STUDY = "09_Davidson_2013"
ALL_CAUSE_MORTALITY = "ACM_Event"
MAJOR_ADVERSE_CARDIAC_EVENT = "MACE_Event"

# ds_10 asks at each follow-up whether the patient has withdrawn. The paired
# `withdraw` column is a Unix timestamp, the date of withdrawal, and is not
# used: a date is not a flag and the flag already says what happened.
WITHDRAWAL_STUDY = "10_Fletcher_2021a"
WITHDRAWAL_FLAG = "withdrawal"

# Longest plausible observation. ds_04 runs to 626 days; anything far beyond
# that would be a date read as a duration.
MAX_OBSERVED_DAYS = 3650

NOT_HARMONIZED = {
    "hospitalisation": "ds_08's service-use battery and ds_09's cardiac admissions count "
    "hospital contacts, but over different periods and for different reasons. The "
    "service-use cluster records whether a hospital was used; a harmonized admission "
    "count would mix a cardiac event with a routine stay.",
    "withdrawal_reason": "No study records why a patient left in a form that can be "
    "compared with any other.",
    "length_of_stay": "ds_09 only, and specific to cardiac admissions.",
}


def _flag(df: pd.DataFrame, study_id: str, column: str) -> pd.Series:
    """Read a study's 0/1 event column as a boolean."""
    checks.require_columns(df, study_id, [column], CLUSTER_KEY)
    rows = checks.require_rows(df, study_id, CLUSTER_KEY)
    numeric = pd.to_numeric(df.loc[rows, column], errors="coerce")
    return (numeric > 0).astype("boolean").where(numeric.notna())


def _carry_forward(df: pd.DataFrame, values: pd.Series) -> pd.Series:
    """Give every row of a patient the one answer recorded for them.

    An event is a property of the whole trajectory, not of the visit it was
    written on: ds_10 records a withdrawal at whichever follow-up it happened,
    and ds_04 its survival times once.
    """
    frame = pd.DataFrame(
        {
            "study": df[COLNAME_STUDYID],
            "patient": df["patient_id"],
            "month": pd.to_numeric(df["follow_up_months"], errors="coerce"),
            "value": values,
        }
    )
    answered = frame[frame["value"].notna()].sort_values("month")
    lookup = answered.drop_duplicates(["study", "patient"]).set_index(["study", "patient"])[
        "value"
    ]
    index = pd.MultiIndex.from_arrays([frame["study"], frame["patient"]])
    return pd.Series(lookup.reindex(index).to_numpy(), index=df.index, dtype=values.dtype)


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize deaths, withdrawals and adjudicated cardiac events."""
    harmonized_df = df[ID_COLS].copy()

    died = pd.Series(pd.NA, index=df.index, dtype="boolean")
    observed = pd.Series(pd.NA, index=df.index, dtype="Float64")

    checks.require_columns(
        df, SURVIVAL_STUDY, [DAYS_UNTIL_DEATH, DAYS_UNTIL_CENSORING], CLUSTER_KEY
    )
    survival_rows = checks.require_rows(df, SURVIVAL_STUDY, CLUSTER_KEY)
    to_death = pd.to_numeric(df.loc[survival_rows, DAYS_UNTIL_DEATH], errors="coerce")
    to_censoring = pd.to_numeric(df.loc[survival_rows, DAYS_UNTIL_CENSORING], errors="coerce")
    # A patient with neither time is not under observation at all, so they are
    # missing rather than recorded as alive.
    known = to_death.notna() | to_censoring.notna()
    died.loc[survival_rows] = to_death.notna().astype("boolean").where(known)
    end_of_observation = to_death.fillna(to_censoring)
    observed.loc[survival_rows] = checks.check_range(
        end_of_observation, (0, MAX_OBSERVED_DAYS), CLUSTER_KEY, f"{SURVIVAL_STUDY} days"
    ).astype("Float64")

    died.loc[df[COLNAME_STUDYID] == EVENT_STUDY] = _flag(df, EVENT_STUDY, ALL_CAUSE_MORTALITY)

    harmonized_df["died_during_follow_up"] = _carry_forward(df, died)
    harmonized_df["days_observed"] = _carry_forward(df, observed).astype("Int64")

    withdrew = pd.Series(pd.NA, index=df.index, dtype="boolean")
    withdrew.loc[df[COLNAME_STUDYID] == WITHDRAWAL_STUDY] = _flag(
        df, WITHDRAWAL_STUDY, WITHDRAWAL_FLAG
    )
    harmonized_df["withdrew_from_study"] = _carry_forward(df, withdrew)

    cardiac = pd.Series(pd.NA, index=df.index, dtype="boolean")
    cardiac.loc[df[COLNAME_STUDYID] == EVENT_STUDY] = _flag(
        df, EVENT_STUDY, MAJOR_ADVERSE_CARDIAC_EVENT
    )
    harmonized_df["had_major_adverse_cardiac_event"] = _carry_forward(df, cardiac)

    return harmonized_df[ID_COLS + HARMONIZED_COLS]


COLUMN_PROVENANCE = {
    "died_during_follow_up": {
        "description": "Died at any point during the trial's follow-up.",
        "transformation": (
            "ds_04 records a time to death for those who died and a time to censoring "
            "for the rest, so a recorded death time is the event. ds_09 adjudicates "
            "all-cause mortality as a yes/no. Confirmed against ds_04's publication: "
            "10 plus 13 deaths by arm, and 23 patients with a death time."
        ),
        "source_columns": {
            SURVIVAL_STUDY: DAYS_UNTIL_DEATH,
            EVENT_STUDY: ALL_CAUSE_MORTALITY,
        },
        "coverage_warning": "2 studies of 30. For the other 28 a missing follow-up "
        "cannot be distinguished from a death.",
    },
    "days_observed": {
        "description": "Days from randomisation to death or to the end of observation.",
        "transformation": (
            "The death time where one exists, otherwise the censoring time. Available "
            "for one study only, so this is survival information for ds_04 and nothing "
            "else."
        ),
        "source_columns": {SURVIVAL_STUDY: f"{DAYS_UNTIL_DEATH}, {DAYS_UNTIL_CENSORING}"},
    },
    "withdrew_from_study": {
        "description": "Withdrew from the trial before the end of follow-up.",
        "transformation": (
            "Asked at each follow-up visit and carried across the patient's rows. The "
            "paired `withdraw` column holds Unix timestamps, the date of withdrawal, "
            "and is deliberately not read as a flag."
        ),
        "source_columns": {WITHDRAWAL_STUDY: WITHDRAWAL_FLAG},
        "coverage_warning": "1 study of 30.",
    },
    "had_major_adverse_cardiac_event": {
        "description": "Adjudicated major adverse cardiac event during follow-up.",
        "transformation": "Taken as adjudicated by the study. One study only.",
        "source_columns": {EVENT_STUDY: MAJOR_ADVERSE_CARDIAC_EVENT},
        "coverage_warning": "1 study of 30, and specific to a post-ACS cohort.",
    },
}

CONSUMPTION = {
    "sources": {
        SURVIVAL_STUDY: [DAYS_UNTIL_DEATH, DAYS_UNTIL_CENSORING],
        EVENT_STUDY: [ALL_CAUSE_MORTALITY, MAJOR_ADVERSE_CARDIAC_EVENT],
        WITHDRAWAL_STUDY: [WITHDRAWAL_FLAG],
    },
    "superseded": {},
    "review": {
        "death_t": "ds_11: labelled 'Thought-of-death(Priorities)'. A suicidal-ideation "
        "item, not vital status, despite the name.",
        "phq2wk_dead_di_t": "ds_11: 'Thoughts that you would be better off dead', the "
        "PHQ-9 suicidality item.",
        "cesd_item_thought_about_death": "ds_32: the same item in the CES-D.",
        "withdraw": "ds_10: Unix timestamps, the date of withdrawal rather than a flag.",
        "MI_Event": "ds_09: myocardial infarction during follow-up, inside MACE_Event.",
        "total_los": "ds_09: hospital length of stay. See NOT_HARMONIZED.",
    },
    "conditional_on": {},
}
