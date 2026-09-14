"""Cluster: baseline psychotropic medication.

Whether a patient was already taking an antidepressant when they entered the
trial is one of the strongest baseline covariates in a depression study: it
separates treatment-naive patients from those whose depression has already
failed a drug, and the trials themselves differ enormously on it, from 22% to
88% of their cohorts.

No existing script harmonizes it, and it is not one of the Iezzoni dimensions,
which describe illness rather than its treatment. It is proposed here as its
own cluster for the same reason the instruments were: it does not fit anywhere
else and it is too important to leave in the unclustered pile.

Three of the five studies were validated against their own publications:

* ds_26 Salisbury reports "taking antidepressants 258/288 (90%)" and
  "251/289 (87%)" by arm; this column gives 88.2%.
* ds_09 Davidson reports 27 active-treatment and 26 usual-care patients
  already taking one, 53 of 150; this column gives 35.3%.
* ds_08 Coventry's Table 2 reports 59 and 73 prescribed antidepressants by
  arm, 132 patients; this column gives 132 of 360.

ds_12 was dropped from the cluster after checking when its prescriptions were
written: see ATC_NOT_BASELINE.

A near miss worth recording: ds_10's ``ad_rec`` looks like an antidepressant
flag and is not. Its Stata codebook reads "Anxiety/Depression (EQ-5D-5L
yesno)", so "ad" is the EQ-5D dimension. Taking the name at face value would
have invented an 81.6% antidepressant rate for that study.
"""

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.harmonization_column_clusters import checks
from collaborative_care_analysis.harmonization_column_clusters.concat import ID_COLS

CLUSTER_KEY = "medication"
HARMONIZED_COLS = ["is_taking_antidepressant"]

# {study: (column, values meaning yes, values meaning no)}
ANTIDEPRESSANT_SOURCES = {
    # Text categories: "Am currently taking", "Have taken in the past",
    # "Have never taken". Only the first is current use.
    "08_Coventry_2015": (
        "antidepressants",
        {"am currently taking"},
        {"have taken in the past", "have never taken"},
    ),
    "09_Davidson_2013": ("cur_antidep", {"1.0", "1"}, {"0.0", "0"}),
    "11_Fletcher_2021b": ("antidepressants_0", {"1.0", "1", "yes"}, {"0.0", "0", "no"}),
    "26_Salisbury_2016": ("d_4_1_current_antidepressant", {"1.0", "1"}, {"0.0", "0"}),
}

# ds_12 records drugs as ATC codes and is deliberately NOT used here. Its
# antidepressant codes (N06A) sit almost entirely on the 6- and 12-month rows:
# 294 and 287 patients against 4 at baseline. The columns without a T1/T2/T3
# suffix are not baseline columns, as the names suggest, so reading them would
# have recorded prescriptions written during the trial as a starting
# characteristic. 351 of 623 patients have such a code at some point, which is
# a real and interesting number, but it is a treatment outcome, not a baseline
# covariate.
ATC_NOT_BASELINE = {
    "12_Gensichen_2009": "N06A codes appear at months 6 and 12 (294 and 287 patients) "
    "and for only 4 patients at baseline, so they record prescriptions during the "
    "trial rather than on entry."
}

NOT_HARMONIZED = {
    "adherence": "ds_19, ds_21, ds_22, ds_29 and ds_33 record medication adherence, but as "
    "a self-report scale in some studies and a pill count in others, and ds_08 as days "
    "missed per month per drug. Different constructs on different scales.",
    "dose": "ds_21's Antidepress_dose is labelled 'Knowledge of dose of antidepressants', "
    "which measures what the patient knows, not what they take.",
    "psychotropic_classes": "Antipsychotics and anxiolytics are derivable from ds_12's ATC "
    "codes (N05A 8.7%, N05B 13.5%) but appear in no other study.",
}


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize baseline antidepressant use."""
    harmonized_df = df[ID_COLS].copy()
    values = pd.Series(pd.NA, index=df.index, dtype="boolean")

    for study_id, (column, yes, no) in ANTIDEPRESSANT_SOURCES.items():
        checks.require_columns(df, study_id, [column], CLUSTER_KEY)
        rows = checks.require_rows(df, study_id, CLUSTER_KEY)
        text = df.loc[rows, column].astype("string").str.strip().str.lower()
        taken = pd.Series(pd.NA, index=text.index, dtype="boolean")
        taken.loc[text.isin(yes)] = True
        taken.loc[text.isin(no)] = False
        unmapped = text.notna() & taken.isna()
        if unmapped.any():
            logger.warning(
                f"{study_id} {column}: {int(unmapped.sum())} value(s) outside the "
                "documented set are left missing."
            )
        checks.report_mapping(CLUSTER_KEY, study_id, column, df.loc[rows, column], taken)
        values.loc[rows] = taken

    # Baseline attribute: carry the earliest recorded answer for each patient.
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
    harmonized_df["is_taking_antidepressant"] = pd.Series(
        lookup.reindex(index).to_numpy(), index=df.index, dtype="boolean"
    )
    return harmonized_df[ID_COLS + HARMONIZED_COLS]


COLUMN_PROVENANCE = {
    "is_taking_antidepressant": {
        "description": "Already taking an antidepressant when entering the trial.",
        "transformation": (
            "Mapped from each study's own column; former use counts as no. Verified "
            "against the published baseline figures for ds_08, ds_09 and ds_26."
        ),
        "source_columns": {s: c for s, (c, _, _) in ANTIDEPRESSANT_SOURCES.items()},
        "excluded": ATC_NOT_BASELINE,
        "not_harmonized": NOT_HARMONIZED,
    }
}

CONSUMPTION = {
    "sources": {s: [c] for s, (c, _, _) in ANTIDEPRESSANT_SOURCES.items()},
    "superseded": {},
    "review": {
        "ad_rec": "ds_10: 'Anxiety/Depression (EQ-5D-5L yesno)', not an antidepressant "
        "flag despite the name. Consumed by the functioning cluster instead.",
        "Antidepress_dose": "ds_21: knowledge of the dose, not use of the drug.",
        "medication_adherence": "ds_22, ds_29, ds_33: adherence on incomparable scales.",
    },
    "conditional_on": {},
}
