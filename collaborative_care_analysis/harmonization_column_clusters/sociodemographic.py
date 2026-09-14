"""Cluster: Iezzoni risk dimension 9 -- socioeconomic and social circumstances.

Only the facts that mean the same thing in every country are harmonized here.
That is a deliberately short list, and the omissions matter more than the
inclusions:

**Education is harmonized only at the level the systems share.** ds_12's
``Schulab`` is a German school-leaving certificate, ds_09's a US degree ladder,
ds_11's a mix of Australian school years and degrees. No common *ordinal* scale
exists: an Abitur is not a college degree and "some college" has no German
counterpart. What every system does distinguish is whether secondary schooling
was completed, and ds_30's codebook fixes the threshold for us by defining its
own three-category variable as "no formal", "primary (1-7 years)" and
"secondary or higher (>7 years)". That boundary is applied to the others, so
the column is a yes/no fact rather than an invented ladder.

**Ethnicity is not harmonized.** ds_08 uses 17 UK census categories, ds_09 the
US federal ones, ds_23 a bare White/Other split. The usual escape, a
white/non-white binary, is a Western frame that means nothing in ds_30's Indian
cohort, where it would label the entire study a minority. Harmonizing it would
need each study's country, which lives in the study-context annotations that
are currently on hold.

**Income and insurance** appear in three and one study respectively, in
national units and national schemes. Too thin and too country-specific.

What survives is employment, living alone, and partnership, each a yes/no fact
that transfers across all four countries.
"""

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.harmonization_column_clusters import checks
from collaborative_care_analysis.harmonization_column_clusters.concat import ID_COLS

CLUSTER_KEY = "sociodemographic"

# ds_24 has no smoking column; it records tobacco use as an entry in the
# comorbidity roster the medical-history side also reads.
ROSTER_COLUMN = "phys_comorbid_name"
ROSTER_TOBACCO = r"tobacco"
# Stands in for a column name where the value is derived from the roster rather
# than read from a column of its own.
ROSTER_SENTINEL = "_tobacco_from_roster"
HARMONIZED_COLS = [
    "is_in_paid_work",
    "lives_alone",
    "has_spouse_or_partner",
    "completed_secondary_education",
    "is_current_smoker",
]

# {column: {study: (raw column, values counting as True, values counting as False)}}
# Spelled out per study because the codes are not consistent and several
# columns carry no value labels, so the mapping is evidence, not convention.
SOURCES = {
    "is_in_paid_work": {
        # Text categories in the export. "Voluntary work" is unpaid by
        # definition and counts as False, as do education and retirement.
        "08_Coventry_2015": (
            "employment",
            {"in paid work"},
            {
                "unemployed",
                "looking after home",
                "voluntary work",
                "unable to work due to health",
                "retired",
                "in education",
                "other",
            },
        ),
        # 0 Employed/working, 1 Sheltered employment, 2 Unemployed and looking,
        # 3 Neither working nor looking. Sheltered employment is paid work.
        "11_Fletcher_2021b": ("employment_0", {"0.0", "1.0"}, {"2.0", "3.0"}),
        # Unlabelled 0/1; 63.1% positive, consistent with a working-age cohort.
        "32_Wells_2000": ("WORK", {"1", "1.0"}, {"0", "0.0"}),
    },
    "lives_alone": {
        # Unlabelled 0/1; 16.3% positive, a plausible living-alone rate.
        "10_Fletcher_2021a": ("live_alone", {"1", "1.0"}, {"0", "0.0"}),
        "11_Fletcher_2021b": ("live_alone_0", {"1.0", "yes"}, {"0.0", "no"}),
    },
    # Renamed from is_partnered, because the two studies do not ask the same
    # question and the name should not imply they do. ds_11 asks whether a
    # spouse lives in the household, ds_32 whether the patient is now married.
    # A married person living apart answers yes to one and no to the other, and
    # an unmarried cohabiting couple the reverse. The shared meaning is "has a
    # spouse or partner", which is what the column claims and no more.
    "has_spouse_or_partner": {
        # "live_spouse_0", part of this study's live-with battery. Value
        # labels give 0 No, 1 Yes.
        "11_Fletcher_2021b": ("live_spouse_0", {"1.0", "yes"}, {"0.0", "no"}),
        # "SCREENER NOW MARRIED". Direction corroborated three ways: the label
        # is a yes/no phrasing, the study's own codebook frequency table gives
        # 739 ones against 617 zeros for a plausible 54.5% married rate, and
        # this repo's existing harmonization_baseline script independently maps
        # 1 to "Married". Not confirmed against a published figure: neither
        # trial report gives a marital breakdown.
        "32_Wells_2000": ("MARRIED", {"1", "1.0"}, {"0", "0.0"}),
    },
    # Completed secondary schooling or more. Codes from each study's own
    # codebook; the threshold is ds_30's "secondary or higher (>7 years)".
    "completed_secondary_education": {
        # 1 Less than high school, 2 Some high school, 3 High school diploma/GED,
        # 4 Trade/vocational, 5 Some college, 6 College graduate, 7 Graduate school.
        "09_Davidson_2013": ("educ_degree", {"3.0", "4.0", "5.0", "6.0", "7.0"}, {"1.0", "2.0"}),
        # 0 Left before Year 10, 1 Year 10, 2 Year 11, 3 Year 12, 4 Certificate/
        # Diploma, 5 Bachelor or higher. Year 12 completes secondary schooling.
        "11_Fletcher_2021b": ("education_0", {"3.0", "4.0", "5.0"}, {"0.0", "1.0", "2.0"}),
        # 1 ohne Schulabschluss, 2 Hauptschule, 3 Realschule, 4 Fachhochschulreife,
        # 5 Abitur, 6 Anderer. Hauptschule is nine years, so it clears the >7
        # threshold; "Anderer" is unclassifiable and left missing.
        "12_Gensichen_2009": ("Schulab", {"2.0", "3.0", "4.0", "5.0"}, {"1.0"}),
        # 0 no formal education, 1 primary (1-7), 2 secondary or higher (>7).
        "30_Srinivasan_2022": ("educ_NPS", {"2.0"}, {"0.0", "1.0"}),
    },
    # Currently smoking. Former smokers count as not current, which both
    # codebooks that define the codes make explicit.
    "is_current_smoker": {
        # 1 Current, 0 Never, 2 Quit <1 year ago, 3 Quit >=1 year ago.
        "04_Bekelman_2018": ("dem_smoke", {"1.0"}, {"0.0", "2.0", "3.0"}),
        # 1 Current, 2 Quit <1 year, 3 Quit >=1 year, 4 Never.
        "05_Bekelman_2015": ("CRF_SMOKE", {"1.0"}, {"2.0", "3.0", "4.0"}),
        "25_Rollman_2017": ("Tobacco Use", {"true"}, {"false"}),
        # ds_24 records tobacco use as an entry in its comorbidity roster, so a
        # patient who lists it is a current user and everyone else is not.
        "24_Rollman_2016": (ROSTER_SENTINEL, {"true"}, {"false"}),
    },
}

NOT_HARMONIZED = {
    "education_level": "The ordinal ladders are not comparable across countries, so only "
    "the completed-secondary threshold is harmonized. ds_13 and ds_26's education columns "
    "have no value labels in any of their supplied material and are left out.",
    "ethnicity": "National category systems that do not map onto each other, and a "
    "white/non-white binary is meaningless for the Indian cohort. Needs study country, "
    "which is in the annotations currently on hold.",
    "income": "Three studies, in national currencies and benefit systems.",
    "insurance": "One study, and a country-specific scheme.",
}


def _read(df: pd.DataFrame, study_id: str, column: str, yes: set, no: set) -> pd.Series:
    rows = df[COLNAME_STUDYID] == study_id
    if column == ROSTER_SENTINEL:
        listed = df.loc[rows, ROSTER_COLUMN].astype("string")
        used = listed.str.contains(ROSTER_TOBACCO, case=False, na=False).astype("boolean")
        # No roster entry means the list was not taken for that row.
        return used.where(listed.notna(), pd.NA)
    text = df.loc[rows, column].astype("string").str.strip().str.lower()
    values = pd.Series(pd.NA, index=text.index, dtype="boolean")
    values.loc[text.isin({v.lower() for v in yes})] = True
    values.loc[text.isin({v.lower() for v in no})] = False
    unmapped = text.notna() & values.isna()
    if unmapped.any():
        logger.warning(
            f"{study_id} {column}: {int(unmapped.sum())} value(s) outside the documented "
            "set are left missing."
        )
    return values


def _at_baseline(df: pd.DataFrame, values: pd.Series) -> pd.Series:
    """Carry each patient's earliest recorded answer across their rows."""
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
    return pd.Series(lookup.reindex(index).to_numpy(), index=df.index, dtype="boolean")


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize the sociodemographic cluster across all studies."""
    harmonized_df = df[ID_COLS].copy()
    for column, per_study in SOURCES.items():
        values = pd.Series(pd.NA, index=df.index, dtype="boolean")
        for study_id, (raw, yes, no) in per_study.items():
            if raw != ROSTER_SENTINEL:
                checks.require_columns(df, study_id, [raw], CLUSTER_KEY)
            rows = checks.require_rows(df, study_id, CLUSTER_KEY)
            mapped = _read(df, study_id, raw, yes, no)
            source = df.loc[rows, ROSTER_COLUMN if raw == ROSTER_SENTINEL else raw]
            checks.report_mapping(CLUSTER_KEY, study_id, raw, source, mapped)
            values.loc[rows] = mapped
        harmonized_df[column] = _at_baseline(df, values)
    return harmonized_df[ID_COLS + HARMONIZED_COLS]


COLUMN_PROVENANCE = {
    column: {
        "description": description,
        "transformation": (
            "Mapped per study from that study's own coded or text values (see SOURCES), "
            "then carried from the patient's earliest recorded answer. Values outside "
            "the documented set are left missing rather than guessed."
        ),
        "source_columns": {
            s: (ROSTER_COLUMN if raw == ROSTER_SENTINEL else raw)
            for s, (raw, _, _) in SOURCES[column].items()
        },
        "not_harmonized": NOT_HARMONIZED,
    }
    for column, description in {
        "is_in_paid_work": "In paid employment at baseline. Voluntary work, education, "
        "home-making and retirement all count as not in paid work.",
        "lives_alone": "Lives alone at baseline.",
        "has_spouse_or_partner": "Has a spouse or partner: married in ds_32, a spouse "
        "in the household in ds_11. The two questions differ, and the harmonized column "
        "claims only what they share. 54.5% and 32.0% respectively; unvalidated against "
        "any publication, since neither trial report gives a marital breakdown.",
        "completed_secondary_education": "Completed secondary schooling or more, using "
        "ds_30's codebook threshold of more than seven years of schooling.",
        "is_current_smoker": "Currently smoking at baseline; former smokers count as no.",
    }.items()
}

CONSUMPTION = {
    "sources": {
        study: sorted(
            {
                ROSTER_COLUMN if raw == ROSTER_SENTINEL else raw
                for col in SOURCES
                for s, (raw, _, _) in SOURCES[col].items()
                if s == study
            }
        )
        for study in {s for col in SOURCES for s in SOURCES[col]}
    },
    "superseded": {},
    "review": {
        "Schulab": "ds_12: German school-leaving certificate. See NOT_HARMONIZED.",
        "educ_degree": "ds_09: US degree ladder. See NOT_HARMONIZED.",
        "education_0": "ds_11: Australian school years and degrees. See NOT_HARMONIZED.",
        "ethnic": "ds_08: 17 UK census categories. See NOT_HARMONIZED.",
        "race": "US federal race categories in several studies. See NOT_HARMONIZED.",
    },
    "conditional_on": {},
}
