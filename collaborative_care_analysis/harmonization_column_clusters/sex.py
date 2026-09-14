"""Cluster: Iezzoni risk dimension 2 -- sex.

Produces one harmonized column, ``sex`` (categorical: Male/Female/Other),
broadcast within patient like age. Unlike age, no naming ambiguity: sex does
not vary by follow-up, so a plain ``sex`` is unambiguous.

Every study needs its own explicit mapping -- numeric direction is NOT
consistent across studies (e.g. ds_04 Bekelman: 1=male, vs ds_12 Gensichen:
1=female), so no shortcut/shared dict is safe. See SEX_MAPPINGS.

ds_29 Simon 2011 contributes nothing: its export carries Age and Sex columns
upstream, but both are empty for all 208 patients, so its loader drops them
rather than pass on two all-null columns.
"""

import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.harmonization_column_clusters.concat import (
    ID_COLS,
    broadcast_within_patient,
)
from collaborative_care_analysis.utils import map_with_check

CLUSTER_KEY = "sex"
HARMONIZED_COLS = ["sex"]

# Per-study raw source column and its coded -> descriptive mapping. Verified
# against each study's own codebook/source file, not assumed from naming; the
# per-study comments below record where a choice needed one.
SEX_SOURCE_COLUMNS = {
    "02_Aragones_2012": "sex",
    "03_Aragones_2019": "SEX",
    "04_Bekelman_2018": "gender",
    "05_Bekelman_2015": "CRF_GENDER",
    # sex3, not sex2: sex3 is the only one of the two listed in this study's
    # own shipped codebook (sex2 is absent from it entirely). 98.8% agree
    # anyway; sex2 is superseded, not used.
    "08_Coventry_2015": "sex3",
    "09_Davidson_2013": "sex",
    "10_Fletcher_2021a": "gender",
    # gender_0, not gender_t: gender_t is a second (toolkit-form) measurement
    # that agrees with gender_0 99.1% of the time but is binary-only, so it
    # can't represent the "Other" respondents gender_0 captures. Superseded.
    "11_Fletcher_2021b": "gender_0",
    "12_Gensichen_2009": "Sex",
    "13_Hölzel_2018": "Geschlecht",
    "14_Katon_1995": "sex",
    "15_Katon_1996": "sex",
    "16_Katon_1999": "sex",
    "17_Katon_2001": "gender",
    "18_Katon_2004": "Sex",
    "19_Katon_2010": "SEX",
    "20_Patel_2010": "Sex",
    "21_Richards_2008": "Sex",
    "22_Richards_2013": "Sex",
    "23_Rollman_2009": "Sex",
    "24_Rollman_2016": "female",
    "25_Rollman_2017": "female",
    "26_Salisbury_2016": "d_13_1_gender",
    "27_Simon_2000": "sex",
    "28_Simon_2004": "Sex",
    "30_Srinivasan_2022": "sex",
    # Direction (1=female) confirmed against the paper: "65% were women"
    # matches this column's observed mean (0.649) almost exactly.
    "31_Unützer_2002": "female",
    "32_Wells_2000": "FEMALE",
    # Source .dta's own value labels are inconsistently cased ('female' vs
    # 'Male') -- a genuine source quirk, not introduced by this pipeline.
    "33_Zimmerman_2016": "Sex",
}

# Each study's own coded/labelled value -> descriptive Male/Female/Other,
# verified via that study's codebook/source file.
# Numeric direction is NOT consistent across studies -- no shared dict is safe.
SEX_MAPPINGS = {
    "02_Aragones_2012": {0: "Female", 1: "Male"},
    "03_Aragones_2019": {0: "Female", 1: "Male"},
    "04_Bekelman_2018": {1.0: "Male", 2.0: "Female"},
    "05_Bekelman_2015": {1.0: "Male", 2.0: "Female"},  # same codebook as ds_04
    "08_Coventry_2015": {"Female": "Female", "Male": "Male"},
    "09_Davidson_2013": {1: "Male", 2: "Female"},
    # {0: Male, 1: Female, 2: Other} -- includes non-binary respondents.
    "10_Fletcher_2021a": {0.0: "Male", 1.0: "Female", 2.0: "Other"},
    "11_Fletcher_2021b": {0.0: "Male", 1.0: "Female", 2.0: "Other"},
    # Geschlecht (Praxisangabe): 1=weiblich (female), 2=männlich (male).
    "12_Gensichen_2009": {1.0: "Female", 2.0: "Male"},
    # GI_B1_Geschlecht: 1=männlich, 2=weiblich. Reversed vs ds_12 -- each
    # study's direction is independent, per the module docstring.
    "13_Hölzel_2018": {1.0: "Male", 2.0: "Female"},
    "14_Katon_1995": {"F": "Female", "M": "Male"},
    "15_Katon_1996": {"F": "Female", "M": "Male"},
    "16_Katon_1999": {"F": "Female", "M": "Male"},
    "17_Katon_2001": {0: "Male", 1: "Female"},
    "18_Katon_2004": {"Female": "Female", "Male": "Male"},
    "19_Katon_2010": {"F": "Female", "M": "Male"},
    "20_Patel_2010": {0: "Female", 1: "Male"},
    "21_Richards_2008": {0: "Female", 1: "Male"},
    "22_Richards_2013": {0: "Female", 1: "Male"},
    "23_Rollman_2009": {0: "Female", 1: "Male"},
    "24_Rollman_2016": {"Yes": "Female", "No": "Male"},
    "25_Rollman_2017": {"Yes": "Female", "No": "Male"},
    # readme value label "hl1cd_13_1_gender": 1=Male, 2=Female.
    "26_Salisbury_2016": {1.0: "Male", 2.0: "Female"},
    "27_Simon_2000": {"F": "Female", "M": "Male"},
    "28_Simon_2004": {0: "Female", 1: "Male"},
    # 3=transgender is in the source's coding scheme but has 0 occurrences in
    # this cohort; kept in the mapping so a future export with such a row
    # doesn't fail map_with_check silently -- it would surface as "Other".
    "30_Srinivasan_2022": {1: "Male", 2: "Female", 3: "Other"},
    "31_Unützer_2002": {0: "Male", 1: "Female"},
    "32_Wells_2000": {0: "Male", 1: "Female"},
    # Sex1 value labels are inconsistently cased in the source ('female' vs
    # 'Male'); mapped as-shipped.
    "33_Zimmerman_2016": {"female": "Female", "Male": "Male"},
}

SEX_CATEGORIES = ["Male", "Female", "Other"]


def find_sex_conflicts(df: pd.DataFrame, sex: pd.Series) -> pd.DataFrame:
    """Return one row per (STUDY_ID, patient_id) whose visits disagree on sex.

    Sex is expected constant within a patient; a patient whose own source data
    disagrees across visits is a data-quality conflict, not something to
    silently pick a side on.

    A review entry point, not part of the build: harmonize() applies the same
    rule inline. Call this to see which patients it caught.
    """
    _, n_distinct = broadcast_within_patient(df, sex)
    conflicting = df.loc[n_distinct > 1, [COLNAME_STUDYID, "patient_id"]].drop_duplicates()
    return conflicting.reset_index(drop=True)


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize the sex cluster across all studies in the concatenated export."""
    harmonized_df = df[ID_COLS].copy()
    sex = pd.Series(pd.NA, index=df.index, dtype="object")

    for study_id, source_col in SEX_SOURCE_COLUMNS.items():
        study_rows = df[COLNAME_STUDYID] == study_id
        sex.loc[study_rows] = map_with_check(
            df.loc[study_rows, source_col],
            SEX_MAPPINGS[study_id],
        )

    # Sex is expected constant within a patient. Where a patient's own source
    # disagrees across visits, the patient's sex is set missing rather than
    # picking a side (e.g. keeping baseline) -- see find_sex_conflicts().
    # Affects 1 patient, in ds_05.
    broadcast, n_distinct = broadcast_within_patient(df, sex)
    harmonized_df["sex"] = broadcast.where(n_distinct <= 1)
    harmonized_df["sex"] = harmonized_df["sex"].astype(
        pd.CategoricalDtype(categories=SEX_CATEGORIES)
    )

    return harmonized_df[ID_COLS + HARMONIZED_COLS]


COLUMN_PROVENANCE = {
    "sex": {
        "description": "Sex/gender at study entry (categorical: Male, Female, Other).",
        "transformation": (
            "Per-study source column mapped through that study's own coded->label scheme "
            "(see SEX_MAPPINGS) via map_with_check(), then collapsed to the single non-null "
            "value per (STUDY_ID, patient_id) and broadcast to that patient's follow-up rows. "
            "'Other' is kept as its own category (ds_10, ds_11, ds_30) rather than folded "
            "into Male/Female or dropped. A patient whose own visits disagree on sex is set "
            "missing rather than resolved to one value (find_sex_conflicts()); affects 1 "
            "patient, in ds_05."
        ),
        "source_columns": SEX_SOURCE_COLUMNS,
    },
}

CONSUMPTION = {
    "sources": SEX_SOURCE_COLUMNS,
    "superseded": {
        "sex2": "ds_08: near-duplicate of sex3 (98.8% agree); sex3 is the one actually listed "
        "in this study's own codebook, so sex2 is dropped rather than used.",
        "gender_t": "ds_11: second (toolkit-form) measurement of gender_0 (99.1% agree); "
        "binary-only, so it can't represent gender_0's 'Other' respondents.",
        "gender_collapsed": "ds_10: binary collapse of `gender` that force-folds all 6 "
        "'Other' respondents into Female -- a real information loss, not used.",
    },
    "review": {},
    "conditional_on": {},
}
