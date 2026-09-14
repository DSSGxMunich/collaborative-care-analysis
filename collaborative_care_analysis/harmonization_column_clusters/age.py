"""Cluster: Iezzoni risk dimension 1 -- age.

Produces one harmonized column:

``age_at_baseline``
    Continuous age in years at study entry. Named "at_baseline" deliberately:
    every source column below was verified to hold exactly one value per
    patient across visits, so none of them is an age-at-visit measure that
    would drift over follow-up (harmonize() re-checks this at runtime via
    broadcast_within_patient() and nulls out any patient whose visible data
    disagrees, rather than trusting the claim blindly). Where a study only
    records age on its baseline row, the value is broadcast to that patient's
    other rows, since age at baseline is a time-invariant attribute.

ds_26 Salisbury 2016 recorded age only in bands, never continuously, so it
contributes nothing here. An earlier version emitted a banded
``age_group_at_baseline`` column for it, but that column was populated for one
study and empty for the other 29 -- 96% missing -- which reads as an
availability problem rather than the design decision it was. Salisbury's bands
stay in the raw frame as ``age_categorical`` (0 = <40, 1 = 40-49, 2 = 50-59,
3 = 60-69, 4 = 70+, per its readme value label "age_cat"), flagged for review
rather than dropped, so anyone who wants that study's age can still reach it
deliberately.

Two studies have no age variable of their own: ds_05 Bekelman 2015 and ds_29
Simon 2011. ds_29's export does carry ``Age`` and ``Sex`` columns upstream,
but both are empty for all 208 patients, so its loader drops them rather than
pass on two all-null columns.

``is_age_from_pool2``
    Whether that patient's age was backfilled from the POOL2 participant-level
    export rather than read from the study's own data. False where the study
    supplied it, True where POOL2 did, missing where age is still unknown.

    POOL2 fills 775 patients in three studies: ds_26 Salisbury 2016 completely
    (609 of 609), ds_05 Bekelman 2015 partially (160 of 384), and 6 in ds_12
    Gensichen 2009. ds_29 Simon 2011 has POOL2 rows but its Age column is
    empty there too, so it stays missing -- it is now the only study with no
    age at all. Overall coverage goes from 93.6% to 97.7% of patients.

    The ds_12 six are worth knowing about: five of them are the patients whose
    own gebdatum disagrees across visits, which the conflict rule above
    deliberately sets to missing rather than picking a side between two of the
    study's own values. POOL2 is an independent third source, so filling them
    resolves that standoff rather than arbitrating it -- but it is still an
    external value standing in for a contested internal one, which is exactly
    what the flag is for.

    The ds_05 coverage is *not* a random subset, and the flag exists so that
    this cannot be forgotten. POOL2 is a depression IPD pool and CASA enrolled
    on heart failure, so POOL2 holds that trial's depressed stratum: the 160
    covered patients average PHQ-9 14.5 at baseline against 5.2 for the 224 it
    does not cover (GAD-7 9.2 vs 3.2). Sex and arm are balanced, so this is a
    real selection in POOL2's inclusion, not a broken join. Complete-casing on
    age therefore silently restricts ds_05 to its depressed patients. That may
    well be the right cohort for a depression model, but it has to be a stated
    inclusion criterion -- filter on ``is_age_from_pool2`` to see or exclude
    the backfilled values.
"""

from loguru import logger
import numpy as np
import pandas as pd

from collaborative_care_analysis import pool2
from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.harmonization_column_clusters.concat import (
    ID_COLS,
    broadcast_within_patient,
)

CLUSTER_KEY = "age"
HARMONIZED_COLS = ["age_at_baseline", "is_age_from_pool2"]

# Ages outside this range are treated as data-entry corruption rather than
# real values. Applied uniformly to every study; only ds_11 Fletcher 2021b
# actually has violations (35 patients), and those are recovered from its
# screening age rather than dropped -- see AGE_FALLBACK_COLUMNS.
PLAUSIBLE_AGE_RANGE = (16, 110)

# Per-study continuous age source. One entry per study that has one; the
# comment records why this column rather than a neighbouring candidate.
AGE_SOURCE_COLUMNS = {
    "02_Aragones_2012": "age",
    "03_Aragones_2019": "AGE",
    # "age" (codebook: "derived", "Participant age"), not "dem_age". Both are
    # baseline values -- their difference has median 0.009y and a 5-95% range
    # of +-0.5y, i.e. the same moment, one rounded and one not -- but dem_age
    # is top-coded ("If pt is >89 years of age, his/her age is recorded as
    # 89") whereas the derived age runs to 94.8 uncensored.
    "04_Bekelman_2018": "age",
    "08_Coventry_2015": "age",
    "09_Davidson_2013": "age",
    # Only populated on the baseline wave: this study's loader carries age in
    # the screening/baseline file only, so it is broadcast below.
    "10_Fletcher_2021a": "age",
    # Codebook: "AGE (years)-continuous". Verified against the screening age
    # (age_0): 90.8% agree within one year, median difference +0.44y, so AGE
    # is a baseline-moment measure. 35 patients carry corrupted values (9 of
    # them negative) and fall back to age_0 -- see AGE_FALLBACK_COLUMNS.
    "11_Fletcher_2021b": "AGE",
    # ds_12 Gensichen 2009 is derived from dates, not a column -- see
    # _derive_gensichen_age().
    "13_Hölzel_2018": "Alter",
    "14_Katon_1995": "age",
    "15_Katon_1996": "age",
    "16_Katon_1999": "age",
    "17_Katon_2001": "age",
    "18_Katon_2004": "Age",
    # "Aage" is the source .sav's own spelling, carried through verbatim by
    # the loader; a mechanical rename, not a different construct.
    "19_Katon_2010": "Aage",
    "20_Patel_2010": "Age",
    "21_Richards_2008": "Age",
    "22_Richards_2013": "Age",
    "23_Rollman_2009": "Age",
    "24_Rollman_2016": "age",
    "25_Rollman_2017": "age",
    # ds_26 Salisbury 2016 has banded age only; see REVIEW_COLUMNS.
    "27_Simon_2000": "age",
    "28_Simon_2004": "age",
    "30_Srinivasan_2022": "age",
    "31_Unützer_2002": "AGE",
    "32_Wells_2000": "CALAGE",
    "33_Zimmerman_2016": "Age",
}

# Secondary source used only where the primary is outside PLAUSIBLE_AGE_RANGE.
# Fletcher 2021b's derived AGE is corrupted for 35 patients while the raw
# screening age it was derived from is intact for all 35, so falling back
# recovers every affected patient instead of dropping them to missing.
AGE_FALLBACK_COLUMNS = {
    "11_Fletcher_2021b": "age_0",
}

# Raw columns this cluster accounts for, beyond the sources above. Consumed by
# drops.py to decide what can leave the working frame once age is harmonized.
#
#   "superseded" -- the column's age information is now fully carried by
#                   age_at_baseline, so dropping it loses nothing.
#   "review"     -- age-adjacent but NOT the same construct, or a decision the
#                   user should make consciously. Never dropped automatically.
SUPERSEDED_COLUMNS = {
    # Top-coded duplicate of ds_04's derived `age` (capped at 89).
    "dem_age": "Integer, top-coded age from the demographics form; `age` supersedes it uncapped.",
    # ds_08 Coventry bands, all derived from its own `age`.
    "agegp": "Age band derived from `age`.",
    "patagegp": "Age band derived from `age` (patient-level copy).",
    "ageover65": "Boolean age threshold derived from `age`.",
    "age5064": "Boolean age threshold derived from `age`. NOTE: its source label reads "
    "'Aged 65+', identical to ageover65 -- a source labelling error; the name implies 50-64.",
    # ds_11 Fletcher 2021b variants of the same AGE.
    "AGE_int": "Integer rounding of `AGE`.",
    "AGE_grp": "Age band derived from `AGE`.",
    "AGE_grp3": "3-category age band derived from `AGE`.",
    "age_num_0": "Screening-age duplicate of `age_0`.",
    "age_r_0": "Screening-age duplicate of `age_0`.",
    # ds_12 Gensichen.
    "GebJahr": "Two-digit birth year; same information as `gebdatum` at lower resolution "
    "(99.4% agree with gebdatum's year).",
    "AlterT3": "ds_12: age at the t3 visit. Recoverable as age_at_baseline plus elapsed "
    "time, so it carries no baseline information of its own. NOTE: t3's actual "
    "elapsed time varies 16.0-36.9 months, so age_at_baseline + 24/12 is an "
    "approximation; recompute from exported_datasets if exact age-at-visit is "
    "ever needed.",
    "PHQBeDat": "ds_12: date the baseline PHQ was administered. Visit timing is carried by "
    "follow_up_months per HARMONIZATION_CONVENTIONS.md section 6, and this date "
    "was already used to correct the study's VISIT_MONTHS mapping.",
}

REVIEW_COLUMNS: dict[str, str] = {
    "age_categorical": "ds_26 Salisbury 2016's banded age (0 = <40, 1 = 40-49, 2 = 50-59, "
    "3 = 60-69, 4 = 70+, per its readme value label 'age_cat'). This study never recorded "
    "continuous age, so nothing in this cluster supersedes it and it must not be dropped: "
    "it is the only age information ds_26 has.",
}

# Birth dates. Dropped under the rule "drop the birth date where age at baseline
# is present" -- enforced per study by drops.py rather than assumed, so a study
# whose age derivation failed keeps the only column that could recover it.
# Dropping these also removes a direct identifier from the working frame; the
# columns remain in exported_datasets, which stays the system of record.
BIRTH_DATE_COLUMNS = {
    "dob": "ds_08: date of birth; age_at_baseline covers 100% of its patients.",
    "dob2": "ds_08: date of birth (second copy); same.",
    "DOB": "ds_11: date of birth; age_at_baseline covers 100% of its patients.",
    "dob_0": "ds_11: screening date of birth; same.",
    "gebdatum": "ds_12: date of birth, and the input to this study's derived age; "
    "age_at_baseline now covers 616/623 patients (5 more excluded for a conflicting birth date).",
}

_GENSICHEN_STUDY_ID = "12_Gensichen_2009"
_ISO_DATE = "%Y-%m-%d"
_DAYS_PER_YEAR = 365.25


# ds_12 baseline-visit dates, in preference order. All three are t0 dates and
# agree closely (Befragun median 3 days from PHQBeDat, PHQ2BDat median -8 days
# -- negligible against an age in years), so coalescing them covers 5 patients
# who have a birth date but no PHQ date. t3's DatumBef is deliberately absent:
# it sits ~26 months later and would overstate baseline age by about two years.
_GENSICHEN_BASELINE_DATE_COLUMNS = ["PHQBeDat", "Befragun", "PHQ2BDat"]

# The 5 patients ds_12's own loader flags at import time: their birth date
# (gebdatum) disagreed with baseline at a non-baseline visit, and the loader's
# broadcast_time_independent() silently keeps the baseline value rather than
# raising (see its docstring). By the time we read the export that conflict
# is invisible -- only the "winning" value survives -- so it can't be detected
# from the data itself; these IDs are the loader's own printed diagnostic.
# We don't know which recorded birth date is right, so -- consistent with how
# a conflicting sex value is handled (see sex.find_sex_conflicts()) -- age is
# set missing for these patients rather than trusted from either one.
_GENSICHEN_CONFLICTING_GEBDATUM_PATIENT_IDS = {1611, 5401, 5502, 5604, 6605}


def _derive_gensichen_age(study_df: pd.DataFrame) -> pd.Series:
    """Age at baseline for ds_12 Gensichen 2009, which has no age column.

    PRoMPT recorded a birth date (``gebdatum``) and several baseline-visit
    dates, all as ISO dates, so baseline age is their difference -- no assumed
    enrollment year is needed. Coalescing the baseline dates covers 616 of 623
    patients with no implausible values, minus the 5 excluded for a conflicting
    birth date (see ``_GENSICHEN_CONFLICTING_GEBDATUM_PATIENT_IDS``).

    ``GebJahr`` is deliberately not used: despite the name meaning "birth
    year" its values run 20-87, which are the two-digit years (99.4% agree
    with ``gebdatum``'s year), so it would need the same date arithmetic at
    lower resolution. ``AlterT3`` is also unused -- it is age at the t3 visit,
    roughly 24 months after baseline, so broadcasting it would overstate
    baseline age by about two years.
    """
    birth_date = pd.to_datetime(study_df["gebdatum"], format=_ISO_DATE, errors="raise")

    baseline_date = pd.Series(pd.NaT, index=study_df.index, dtype="datetime64[ns]")
    for column in _GENSICHEN_BASELINE_DATE_COLUMNS:
        baseline_date = baseline_date.fillna(
            pd.to_datetime(study_df[column], format=_ISO_DATE, errors="raise")
        )

    age = (baseline_date - birth_date).dt.days / _DAYS_PER_YEAR
    conflicting = study_df["patient_id"].isin(_GENSICHEN_CONFLICTING_GEBDATUM_PATIENT_IDS)
    return age.where(~conflicting)


def _raw_age_per_row(df: pd.DataFrame) -> pd.Series:
    """Assemble one raw age value per row, applying each study's own source."""
    raw_age = pd.Series(np.nan, index=df.index, dtype="float64")

    for study_id, source_col in AGE_SOURCE_COLUMNS.items():
        study_rows = df[COLNAME_STUDYID] == study_id
        values = pd.to_numeric(df.loc[study_rows, source_col], errors="raise")

        fallback_col = AGE_FALLBACK_COLUMNS.get(study_id)
        if fallback_col is not None:
            implausible = ~values.between(*PLAUSIBLE_AGE_RANGE)
            fallback = pd.to_numeric(df.loc[study_rows, fallback_col], errors="raise")
            values = values.where(~implausible, fallback)

        raw_age.loc[study_rows] = values

    gensichen_rows = df[COLNAME_STUDYID] == _GENSICHEN_STUDY_ID
    raw_age.loc[gensichen_rows] = _derive_gensichen_age(df.loc[gensichen_rows])

    # Uniform plausibility filter: anything still outside the range after a
    # study's own fallback is data-entry corruption, so it becomes missing
    # rather than silently entering a regression.
    return raw_age.where(raw_age.between(*PLAUSIBLE_AGE_RANGE))


def _pool2_age_per_row(df: pd.DataFrame) -> pd.Series:
    """Age per row from POOL2, aligned to df's index. All-missing if unavailable.

    POOL2 ships as a zip that has to be extracted before use. A machine that
    has not done so is a setup state, not a broken build, so this warns and
    contributes nothing rather than failing the whole cluster -- but it warns
    loudly, because the alternative is age coverage silently differing between
    two checkouts of the same commit.
    """
    try:
        pool = pool2.load()
    except FileNotFoundError as exc:
        logger.warning(
            f"{CLUSTER_KEY}: POOL2 is not extracted, so no age is backfilled "
            f"from it and ds_26/ds_05 stay missing. {exc}"
        )
        return pd.Series(np.nan, index=df.index, dtype="float64")

    lookup = pool.set_index([COLNAME_STUDYID, "patient_id"])["age"]
    keys = pd.MultiIndex.from_arrays([df[COLNAME_STUDYID], df["patient_id"].astype("string")])
    values = pd.Series(lookup.reindex(keys).to_numpy(), index=df.index, dtype="float64")
    # POOL2 ages get the same plausibility filter as every other source.
    return values.where(values.between(*PLAUSIBLE_AGE_RANGE))


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize the age cluster across all studies in the concatenated export."""
    harmonized_df = df[ID_COLS].copy()
    raw_age = _raw_age_per_row(df)

    # Age is expected constant within a patient, so collapsing to the single
    # non-null value and broadcasting it fills the follow-up rows of studies
    # that record age on the baseline row only (e.g. ds_10 Fletcher 2021a).
    # Where a patient's own visible data disagrees across visits, age is set
    # missing rather than resolved to "first" -- the same rule as sex (see
    # sex.find_sex_conflicts()). This only catches conflicts visible in the
    # export; ds_12's are pre-resolved upstream and handled separately above.
    broadcast, n_distinct = broadcast_within_patient(df, raw_age)
    # Nullable Float64, not plain float64: three studies record no age at all,
    # and HARMONIZATION_CONVENTIONS section 5 asks for a nullable dtype wherever
    # a value can be missing.
    own_age = broadcast.where(n_distinct <= 1).astype("Float64")

    # POOL2 is a fallback, never an override: a study's own age always wins
    # where it has one, so backfilling can only add coverage, never silently
    # change a value the study itself reported.
    pool2_age = _pool2_age_per_row(df).astype("Float64")
    filled_from_pool2 = own_age.isna() & pool2_age.notna()
    age = own_age.where(~filled_from_pool2, pool2_age)

    if filled_from_pool2.any():
        by_study = df.loc[filled_from_pool2].groupby(COLNAME_STUDYID)["patient_id"].nunique()
        logger.info(
            f"{CLUSTER_KEY}: backfilled age from POOL2 for "
            f"{int(filled_from_pool2.sum())} row(s) across "
            f"{len(by_study)} study/studies: {by_study.to_dict()}."
        )

    harmonized_df["age_at_baseline"] = age
    # False = the study's own, True = POOL2, missing = no age at all. Anything
    # that must not lean on backfilled values can filter on this column.
    harmonized_df["is_age_from_pool2"] = filled_from_pool2.where(age.notna()).astype("boolean")

    return harmonized_df[ID_COLS + HARMONIZED_COLS]


# --- Cluster metadata -------------------------------------------------------
# Everything downstream tooling needs to know about this cluster lives here, so
# one cluster is one file: build.py reads COLUMN_PROVENANCE to write
# column_mapping.json, and drops.py reads CONSUMPTION to decide what can leave
# the working frame.

COLUMN_PROVENANCE = {
    "age_at_baseline": {
        "description": "Continuous age in years at study entry.",
        "transformation": (
            "Per-study source column taken verbatim (see source_columns), coerced to numeric, "
            "then collapsed to the single non-null value per (STUDY_ID, patient_id) and "
            "broadcast to that patient's follow-up rows. Every source was verified constant "
            "within patient, so no study contributes an age-at-visit measure. Values outside "
            f"{PLAUSIBLE_AGE_RANGE} are treated as corruption and set missing. ds_11 Fletcher "
            "2021b falls back to its screening age (age_0) where the derived AGE is "
            "implausible. ds_12 Gensichen 2009 has no age column and is derived as (first "
            "available baseline visit date) - gebdatum, coalescing PHQBeDat, Befragun and "
            "PHQ2BDat. Where a study supplies no age of its own, the value is backfilled "
            "from the POOL2 participant-level export, joined on (STUDY_ID, patient_id); a "
            "study's own age always takes precedence, so the backfill can only add coverage. "
            "See is_age_from_pool2, and note the selection caveat on ds_05 recorded there."
        ),
        "source_columns": {
            **AGE_SOURCE_COLUMNS,
            "12_Gensichen_2009": "gebdatum + PHQBeDat/Befragun/PHQ2BDat (derived)",
            "26_Salisbury_2016": "POOL2 Age (backfill; the study records only bands)",
            "05_Bekelman_2015": "POOL2 Age (backfill; covers its depressed stratum only)",
        },
        "fallback_columns": AGE_FALLBACK_COLUMNS,
    },
    "is_age_from_pool2": {
        "description": (
            "True where age_at_baseline was backfilled from the POOL2 export, False where "
            "the study supplied it, missing where age is unknown."
        ),
        "transformation": (
            "Set True for rows whose own-study age was missing and whose (STUDY_ID, "
            "patient_id) matched a POOL2 row with a plausible Age. POOL2 closes ds_26 "
            "Salisbury 2016 completely (609/609 patients) and ds_05 Bekelman 2015 partially "
            "(160/384). The ds_05 coverage is a selected subset, not a random one: POOL2 is "
            "a depression pool and CASA enrolled on heart failure, so the covered patients "
            "average PHQ-9 14.5 at baseline against 5.2 for the uncovered (GAD-7 9.2 vs "
            "3.2), with sex and arm balanced. Complete-casing on age therefore restricts "
            "ds_05 to its depressed patients; filter on this column to see or exclude that."
        ),
        "source_columns": {
            "26_Salisbury_2016": "POOL2 Age",
            "05_Bekelman_2015": "POOL2 Age",
        },
    },
}

CONSUMPTION = {
    "sources": {
        **AGE_SOURCE_COLUMNS,
        "12_Gensichen_2009": "gebdatum",
    },
    # Conditionally-consumed secondary columns (real study_id -> column), kept
    # structurally separate from "sources" rather than smuggled into it under a
    # fake study_id: drops.py unions both when deciding which studies account
    # for a column, with no string-parsing involved.
    "fallback_sources": AGE_FALLBACK_COLUMNS,
    "superseded": {**SUPERSEDED_COLUMNS, **BIRTH_DATE_COLUMNS},
    "review": REVIEW_COLUMNS,
    # Droppable only where the harmonized value actually covers the patients
    # holding them: {column: harmonized column that must be present}.
    "conditional_on": {column: "age_at_baseline" for column in BIRTH_DATE_COLUMNS},
}
