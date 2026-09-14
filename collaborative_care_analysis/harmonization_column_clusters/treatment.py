"""Cluster: randomised treatment allocation.

Produces the arm a patient was allocated to. This is *allocation only* --
which arm, not what the intervention contained. Classifying the components
of each study's collaborative-care bundle is a separate, deliberately
excluded piece of work; nothing here attempts it.

Three columns:

* ``study_arm`` -- the study's own arm, at full granularity. Multi-arm
  trials keep their arms distinct (ds_28's two active arms, ds_32's
  QI-Meds vs QI-Therapy, ds_25's CCBT vs CCBT+ISG, ds_27's feedback-only
  vs telephone care management) rather than being collapsed to a single
  "intervention". Collapsing is easy later; recovering the distinction
  after the fact is not, and a component-level analysis needs it.
* ``is_randomised`` -- False for participants who are in the dataset but
  were never randomised. Two studies have them, and in both cases the raw
  arm column does not say so on its own (see below).
* ``is_intervention_arm`` -- the binary collapse, for anything that only
  needs treated-vs-control. Missing where ``is_randomised`` is False,
  because those participants have no randomised comparison to belong to.

Every mapping except ds_29 is inherited from the reviewed per-study modules
in ``harmonization_treatment/``; this cluster re-expresses them against the
concatenated frame rather than re-deriving them from the raw files. ds_29
Simon 2011 has no module there -- its mapping is the one added here, and it
is the one to check first if an arm count looks wrong.

Two studies carry participants who were never randomised, and in both the
arm column alone would silently absorb them into the control group:

* ds_10 Fletcher 2021a -- only the minimal/mild and severe prognostic groups
  were randomised. ``group_r_scr`` is 1 for the whole moderate group too, so
  a plain 1 -> control mapping turns 837 real controls into 1264. The
  moderate group is kept (it is a usable usual-care comparison cohort) under
  its own arm label, flagged not randomised.
* ds_24 Rollman 2016 -- the watchful-waiting cohort was randomised only if
  symptoms worsened; "WW never randomized" is exactly that group.

ds_29's arm is constant within every one of its 208 patients, so the
broadcast below is a no-op there; it is applied uniformly anyway because
allocation cannot change within a patient, and a source that disagrees
across a patient's visits is a data problem, not a value to pick a side on.
"""

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.harmonization_column_clusters.concat import (
    ID_COLS,
    broadcast_within_patient,
)
from collaborative_care_analysis.utils import map_with_check

CLUSTER_KEY = "treatment"
HARMONIZED_COLS = ["study_arm", "is_randomised", "is_intervention_arm"]

# Arm label given to participants present in the data but never randomised.
NOT_RANDOMISED_ARM = "usual_care_not_randomised"

# Per-study raw source column for allocation. Inherited from the reviewed
# modules in harmonization_treatment/ -- note how little the naming helps:
# RAND, CLNTYPE, randgrp, assign, grp, gr_est, trt, treatarm, allocation.
ARM_SOURCE_COLUMNS = {
    "02_Aragones_2012": "gr_est",
    "03_Aragones_2019": "GROUP",
    "04_Bekelman_2018": "arm",
    "05_Bekelman_2015": "ARM",
    "08_Coventry_2015": "trt",
    "09_Davidson_2013": "Group",
    # ds_10 needs two columns; see _ds_10_arm().
    "10_Fletcher_2021a": ["group_r_scr", "severity_r"],
    "11_Fletcher_2021b": "group",
    "12_Gensichen_2009": "study_arm",
    "13_Hölzel_2018": "RG",
    "14_Katon_1995": "randgrp",
    "15_Katon_1996": "randgrp",
    "16_Katon_1999": "assign",
    "17_Katon_2001": "grp",
    "18_Katon_2004": "Group",
    "19_Katon_2010": "intervention",
    "20_Patel_2010": "group",
    "21_Richards_2008": "Group",
    "22_Richards_2013": "Group",
    "23_Rollman_2009": "Group",
    "24_Rollman_2016": "group",
    "25_Rollman_2017": "group",
    "26_Salisbury_2016": "allocation",
    "27_Simon_2000": "group",
    "28_Simon_2004": "group",
    "29_Simon_2011": "Group",
    "30_Srinivasan_2022": "treatarm",
    "31_Unützer_2002": "RAND",
    "32_Wells_2000": "CLNTYPE",
    "33_Zimmerman_2016": "Group",
}

# Coded value -> arm label, per study. Numeric direction is not consistent
# across studies (ds_03 uses 0/1, ds_04 uses 1/2, ds_21 uses -1/0/1), so
# every study gets its own explicit dict and map_with_check() raises on any
# code not listed here rather than silently yielding NA.
ARM_MAPPINGS = {
    "02_Aragones_2012": {0: "control", 1: "intervention"},
    "03_Aragones_2019": {0: "control", 1: "intervention"},
    "04_Bekelman_2018": {1: "control", 2: "intervention"},
    "05_Bekelman_2015": {"Usual Care": "control", "Intervention": "intervention"},
    "08_Coventry_2015": {"Control": "control", "Intervention": "intervention"},
    "09_Davidson_2013": {0: "control", 1: "intervention"},
    "11_Fletcher_2021b": {1: "control", 2: "intervention"},
    "12_Gensichen_2009": {1: "control", 2: "intervention"},
    "13_Hölzel_2018": {0: "control", 1: "intervention"},
    "14_Katon_1995": {"Usual Care": "control", "Collaborative Care": "intervention"},
    "15_Katon_1996": {"Usual Care": "control", "Collaborative Care": "intervention"},
    "16_Katon_1999": {"Usual Care": "control", "Collaborative Care": "intervention"},
    "17_Katon_2001": {1.0: "control", 2.0: "intervention"},
    "18_Katon_2004": {"Control": "control", "Intervention": "intervention"},
    "19_Katon_2010": {0: "control", 1: "intervention"},
    "20_Patel_2010": {0: "control", 1: "intervention"},
    # -1 and 0 are both control in this study's own coding.
    "21_Richards_2008": {-1: "control", 0: "control", 1: "intervention"},
    "22_Richards_2013": {0: "control", 1: "intervention"},
    "23_Rollman_2009": {0: "control", 1: "intervention"},
    "24_Rollman_2016": {
        "High Anx UC": "control",
        "High Anx CC": "intervention",
        "WW randomized to UC": "control",
        "WW randomized to CC": "intervention",
        "WW never randomized": NOT_RANDOMISED_ARM,
    },
    "25_Rollman_2017": {
        "Usual Care": "control",
        "CCBT alone": "intervention_CCBT",
        "CCBT+ISG": "intervention_CCBT_ISG",
    },
    "26_Salisbury_2016": {1: "control", 2: "intervention"},
    "27_Simon_2000": {
        "Usual care": "control",
        "Feedback only, no care management": "intervention_feedback_only",
        "Telephone care management": "intervention_telephone_care_management",
    },
    "28_Simon_2004": {
        0: "control",
        1: "intervention_Psychotherapy",
        2: "intervention_TelCare",
    },
    # The one mapping not inherited from a reviewed harmonization_treatment
    # module: ds_29 has none. 208 patients, arm constant within each.
    "29_Simon_2011": {"Control": "control", "Intervention": "intervention"},
    "30_Srinivasan_2022": {0: "control", 1: "intervention"},
    "31_Unützer_2002": {0: "control", 1: "intervention"},
    "32_Wells_2000": {
        "U": "control",
        "M": "intervention_Medication",
        "T": "intervention_Therapy",
    },
    "33_Zimmerman_2016": {"Control": "control", "Intervention": "intervention"},
}

_DS10_MODERATE_PROGNOSTIC_GROUP = 2


def _ds_10_arm(df: pd.DataFrame, study_rows: pd.Series) -> pd.Series:
    """ds_10's arm, with the never-randomised moderate group separated out.

    ``group_r_scr`` codes 1/2 for control/intervention but is also 1 for the
    entire moderate prognostic group, which was never randomised. Mapping it
    alone would fold 427 never-randomised participants into the control arm.
    """
    arm = map_with_check(
        df.loc[study_rows, "group_r_scr"], {1: "control", 2: "intervention"}
    ).astype("string")
    severity = pd.to_numeric(df.loc[study_rows, "severity_r"], errors="raise")
    not_randomised = severity.eq(_DS10_MODERATE_PROGNOSTIC_GROUP)

    conflicting = not_randomised & arm.eq("intervention")
    if conflicting.any():
        raise ValueError(
            f"ds_10: {int(conflicting.sum())} row(s) in the non-randomised "
            "moderate prognostic group are coded as intervention; the "
            "severity_r / group_r_scr relationship this cluster relies on "
            "does not hold and the arm assignment cannot be trusted."
        )
    return arm.mask(not_randomised, NOT_RANDOMISED_ARM)


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize treatment allocation across all studies."""
    harmonized_df = df[ID_COLS].copy()
    arm = pd.Series(pd.NA, index=df.index, dtype="object")

    for study_id, source in ARM_SOURCE_COLUMNS.items():
        study_rows = df[COLNAME_STUDYID] == study_id
        if not study_rows.any():
            logger.warning(
                f"{CLUSTER_KEY}/{study_id}: declared as an arm source but no "
                "rows for it are present in this frame."
            )
            continue
        if study_id == "10_Fletcher_2021a":
            arm.loc[study_rows] = _ds_10_arm(df, study_rows)
            continue
        arm.loc[study_rows] = map_with_check(df.loc[study_rows, source], ARM_MAPPINGS[study_id])

    # Allocation cannot change within a patient. Where a patient's source
    # disagrees across their visits the arm is set missing rather than
    # resolved to one value, and the count is logged -- the same rule the
    # sex cluster applies, for the same reason.
    broadcast, n_distinct = broadcast_within_patient(df, arm)
    conflicting = n_distinct > 1
    if conflicting.any():
        n_patients = (
            df.loc[conflicting, [COLNAME_STUDYID, "patient_id"]].drop_duplicates().shape[0]
        )
        logger.warning(
            f"{CLUSTER_KEY}: {n_patients} patient(s) have more than one "
            "distinct study_arm across their own visits; their arm is set "
            "missing rather than resolved to one value."
        )
    arm = broadcast.where(~conflicting)

    harmonized_df["study_arm"] = arm.astype("category")

    is_randomised = pd.Series(pd.NA, index=df.index, dtype="boolean")
    is_randomised.loc[arm.notna()] = arm[arm.notna()].ne(NOT_RANDOMISED_ARM)
    harmonized_df["is_randomised"] = is_randomised

    randomised_arm = arm.where(is_randomised.fillna(False))
    is_intervention = pd.Series(pd.NA, index=df.index, dtype="boolean")
    known = randomised_arm.notna()
    is_intervention.loc[known] = randomised_arm[known].str.startswith("intervention")
    harmonized_df["is_intervention_arm"] = is_intervention

    for column in HARMONIZED_COLS:
        covered = harmonized_df[column].notna()
        logger.debug(
            f"{CLUSTER_KEY}/{column}: {int(covered.sum())} row(s) across "
            f"{df.loc[covered, COLNAME_STUDYID].nunique()} studies."
        )

    return harmonized_df[ID_COLS + HARMONIZED_COLS]


COLUMN_PROVENANCE = {
    "study_arm": {
        "description": (
            "Randomised treatment allocation, at the study's own granularity. "
            "Multi-arm trials keep their arms distinct rather than collapsing "
            "to one 'intervention' label. Participants who were never "
            f"randomised carry '{NOT_RANDOMISED_ARM}'."
        ),
        "transformation": (
            "Per-study source column mapped through that study's own coded->label "
            "scheme (see ARM_MAPPINGS) via map_with_check(), which raises on any "
            "code not listed, then collapsed to the single non-null value per "
            "(STUDY_ID, patient_id) and broadcast to that patient's rows. A "
            "patient whose own visits disagree on arm is set missing rather than "
            "resolved. ds_10 additionally needs severity_r to separate the "
            "never-randomised moderate prognostic group, which group_r_scr codes "
            "as 1 alongside the real controls. Every mapping except ds_29 is "
            "inherited from the reviewed modules in harmonization_treatment/."
        ),
        "source_columns": ARM_SOURCE_COLUMNS,
    },
    "is_randomised": {
        "description": (
            "False for participants present in the dataset who were never "
            "randomised (ds_10's moderate prognostic group, ds_24's watchful-"
            "waiting participants whose symptoms never worsened); True otherwise."
        ),
        "transformation": (
            f"study_arm != '{NOT_RANDOMISED_ARM}'. Missing where study_arm is missing."
        ),
        "source_columns": ARM_SOURCE_COLUMNS,
    },
    "is_intervention_arm": {
        "description": (
            "Binary collapse of study_arm: True for any arm labelled "
            "intervention*, False for control. Missing for participants who "
            "were not randomised, who have no randomised comparison to join."
        ),
        "transformation": (
            "study_arm.startswith('intervention'), evaluated only where is_randomised is True."
        ),
        "source_columns": ARM_SOURCE_COLUMNS,
    },
}

CONSUMPTION = {
    "sources": ARM_SOURCE_COLUMNS,
    "superseded": {
        "group": (
            "ds_10: the descriptive arm column ('intervention'/'control'/"
            "'comparison'). group_r_scr plus severity_r is used instead, "
            "because only those two together separate the never-randomised "
            "moderate group from the randomised controls."
        ),
        "treatment_status": (
            "ds_12: post-randomisation treatment actually received, not "
            "allocation. Using it would break the intention-to-treat "
            "comparison this column exists to support."
        ),
        "INTERV": (
            "ds_32: binary collapse of CLNTYPE that merges the QI-Meds and "
            "QI-Therapy arms into one, losing the arm distinction the trial "
            "was designed around."
        ),
    },
    "review": {
        "29_Simon_2011": (
            "The only mapping not inherited from a reviewed "
            "harmonization_treatment module -- that study has none. "
            "Control/Intervention, 208 patients, arm constant within each."
        ),
    },
    "conditional_on": {},
}
