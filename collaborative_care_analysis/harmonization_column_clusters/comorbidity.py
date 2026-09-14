"""Cluster: Iezzoni risk dimension 6 -- coexisting chronic conditions.

Built bottom-up from the concatenated frame: every raw column across all 30
studies was screened against a condition vocabulary covering 13 body systems,
matching column names and codebook labels, independently of what the existing
per-study ``harmonization_medical_history`` scripts happened to extract.

The studies do not share a condition list, so the harmonized columns are the
**common denominator**: the level at which most studies can answer the same
question. A study asking only "do you have heart disease?" and one recording a
myocardial infarction and a congestive heart failure diagnosis separately both
answer ``has_cardiac_disease``; the second also answers
``has_myocardial_infarction``. Rolling up never loses the specific columns, and
never invents a specific answer a study did not give.

Three things this deliberately excludes:

* **Events during follow-up.** ds_09's ``MI_Event``, ``UrgRevasc_Num`` and the
  ``*_los`` length-of-stay columns record what happened after randomisation.
  Those belong to the clinical-override/censoring cluster, not to baseline
  risk, and mixing them would turn an outcome into a covariate.
* **Severity and satisfaction instruments.** ds_08's Seattle Angina
  Questionnaire scores and diabetes-worry scales, ds_09's ``lvef_lt45``, and
  ds_19's ``satisfaction_diabetes_care`` measure how bad or how well-managed a
  condition is, not whether it is present.
* **Lab values.** ds_30 ships HbA1c but no diabetes diagnosis. Thresholding it
  would be a clinical judgment this cluster has no mandate to make, so ds_30
  contributes no diabetes flag.
"""

import re

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.harmonization_column_clusters import checks
from collaborative_care_analysis.harmonization_column_clusters.concat import ID_COLS

CLUSTER_KEY = "comorbidity"

HARMONIZED_COLS = [
    "has_diabetes",
    "has_hypertension",
    "has_cardiovascular_disease",
    "has_cardiac_disease",
    "has_myocardial_infarction",
    "has_heart_failure",
    "has_stroke",
    "has_hyperlipidaemia",
    "has_respiratory_disease",
    "has_cancer",
    "has_musculoskeletal_disorder",
    "has_renal_disease",
    "n_chronic_conditions_reported",
]

# How each study encodes "the patient has this condition".
#
#   binary        0/1, 0.0/1.0 or False/True. The common case.
#   one_blank_no  only the value 1 ever appears and a blank means "no", not
#                 "unknown". ds_02 and ds_03 are coded this way, and reading
#                 them as binary is what caused a live bug in this repo: every
#                 "no" silently became missing.
#   grade         0 is absent and any positive value is present, the magnitude
#                 being an undocumented severity grade.
#   roster        a semicolon-delimited list of condition names per patient.
CODING = {
    "02_Aragones_2012": "one_blank_no",
    "03_Aragones_2019": "one_blank_no",
    "12_Gensichen_2009": "icd_codes",
    "24_Rollman_2016": "roster",
    "25_Rollman_2017": "binary",
}

# Columns whose value set contradicts their documentation, handled explicitly
# rather than silently coerced.
UNDOCUMENTED_CODES = {
    # Its codebook says "Cardiovascular Disease (1/0)", but the data holds 1
    # (52 patients) and 2 (4 patients) and never 0. The 4 twos are undocumented.
    ("02_Aragones_2012", "CARDIOVASC"): {2.0},
}

# {harmonized column: {study: [raw columns]}}. A patient is positive when ANY
# of that study's listed columns is positive, which is what makes the roll-up
# work: ds_23's separate MI and heart-failure flags and ds_31's single HEART
# both feed has_cardiac_disease.
SOURCES: dict[str, dict[str, list[str]]] = {
    "has_diabetes": {
        "02_Aragones_2012": ["DIABETES"],
        "03_Aragones_2019": ["DIABETES"],
        "04_Bekelman_2018": ["crf_dm"],
        "05_Bekelman_2015": ["CRF_DM"],
        "08_Coventry_2015": ["diabetes"],
        "09_Davidson_2013": ["diabetes_mhc"],
        "13_Hölzel_2018": ["CDI_16"],
        "19_Katon_2010": ["DIABETIC"],
        "22_Richards_2013": ["Com_e_HaveIt"],
        "23_Rollman_2009": ["DM_0"],
        "25_Rollman_2017": ["Diabetes"],
        "31_Unützer_2002": ["DIAB"],
    },
    "has_hypertension": {
        "02_Aragones_2012": ["HYPERT"],
        "05_Bekelman_2015": ["CRF_HTN"],
        "22_Richards_2013": ["Com_d_HaveIt"],
        "23_Rollman_2009": ["HPT_0"],
        "25_Rollman_2017": ["Hypertension"],
        "31_Unützer_2002": ["HIGHBP"],
    },
    # The umbrella: angina, infarction, heart failure, coronary disease, or a
    # study's own undifferentiated "heart disease".
    "has_cardiac_disease": {
        "04_Bekelman_2018": ["crf_mi"],
        "05_Bekelman_2015": ["CRF_MI"],
        "08_Coventry_2015": ["chd"],
        "13_Hölzel_2018": ["CDI_1", "CDI_2", "CDI_3"],
        "19_Katon_2010": ["HEARTDIS"],
        "22_Richards_2013": ["Com_c_HaveIt"],
        "23_Rollman_2009": ["MI_0", "CHF_0"],
        "25_Rollman_2017": [
            "Myocardial Infarction",
            "Congestive Heart Failure",
            "Coronary Artery Disease",
            "Other I cardiovascular",
        ],
        "31_Unützer_2002": ["HEART"],
    },
    "has_myocardial_infarction": {
        "04_Bekelman_2018": ["crf_mi"],
        "05_Bekelman_2015": ["CRF_MI"],
        "13_Hölzel_2018": ["CDI_3"],
        "23_Rollman_2009": ["MI_0"],
        "25_Rollman_2017": ["Myocardial Infarction"],
    },
    "has_heart_failure": {
        "13_Hölzel_2018": ["CDI_2"],
        "23_Rollman_2009": ["CHF_0"],
        "25_Rollman_2017": ["Congestive Heart Failure"],
    },
    "has_stroke": {
        "13_Hölzel_2018": ["CDI_12"],
        "23_Rollman_2009": ["CVA_0"],
        "25_Rollman_2017": ["Stroke/TIA"],
    },
    "has_respiratory_disease": {
        "02_Aragones_2012": ["RESPIRATORY"],
        "03_Aragones_2019": ["RESPIRATORY"],
        "05_Bekelman_2015": ["CRF_COPD"],
        "13_Hölzel_2018": ["CDI_4"],
        "22_Richards_2013": ["Com_a_HaveIt", "Com_b_HaveIt"],
        "23_Rollman_2009": ["COPD_0"],
        "25_Rollman_2017": [
            "Asthma",
            "Chronic Obstructive Pulmonary Disease",
            "Other Pulmonary Disease",
        ],
        "31_Unützer_2002": ["LUNG"],
    },
    "has_cancer": {
        "02_Aragones_2012": ["CANCER"],
        "03_Aragones_2019": ["CANCER"],
        "04_Bekelman_2018": ["crf_cancer"],
        "13_Hölzel_2018": ["CDI_15"],
        "22_Richards_2013": ["Com_k_HaveIt"],
        "25_Rollman_2017": ["Current Cancer", "History of Cancer"],
        "31_Unützer_2002": ["CANCER"],
    },
    "has_musculoskeletal_disorder": {
        "13_Hölzel_2018": ["CDI_5", "CDI_6"],
        "22_Richards_2013": ["Com_m_HaveIt", "Com_n_HaveIt"],
        "25_Rollman_2017": [
            "Osteoarthritis",
            "Rheumatoid Arthritis",
            "Fibromyalgia",
            "Chronic Back Pain",
            "Chronic Musculoskeletal Pain, not back",
        ],
        "31_Unützer_2002": ["ARTHRIT"],
    },
    "has_hyperlipidaemia": {
        "23_Rollman_2009": ["HLD_0"],
        "25_Rollman_2017": ["Hyperlipidemia"],
    },
    "has_renal_disease": {
        "09_Davidson_2013": ["renal"],
        "22_Richards_2013": ["Com_h_HaveIt"],
        "23_Rollman_2009": ["Renal_0"],
    },
}

# ds_24 records conditions as a semicolon-delimited roster of 49 distinct
# names rather than per-condition columns. Matched case-insensitively as
# substrings of each listed name.
# ds_12 records up to 23 ICD-10 codes per patient ("Wichtige klinische
# Diagnosen", the practice's list of that patient's important diagnoses), which
# is a more precise source than any checklist: the condition families below are
# read straight off the code ranges. As with ds_24's roster, a family not
# listed is taken as absent, since the list is the practice's own record.
ICD_COLUMNS = [f"ICD1{slot:02d}" for slot in range(1, 24)]
ICD_PATTERNS = {
    "has_diabetes": r"\bE1[0-4]",
    "has_hypertension": r"\bI1[0-5]",
    "has_cardiac_disease": r"\bI2[0-5]|\bI50",
    "has_heart_failure": r"\bI50",
    "has_myocardial_infarction": r"\bI2[12]",
    "has_stroke": r"\bI6[0-9]",
    "has_respiratory_disease": r"\bJ4[0-7]",
    "has_cancer": r"\bC[0-9]{2}",
    "has_musculoskeletal_disorder": r"\bM[0-9]{2}",
    "has_renal_disease": r"\bN1[789]",
    "has_hyperlipidaemia": r"\bE78",
}

ROSTER_COLUMN = "phys_comorbid_name"
# Timing for the roster, and a genuine limitation. It is NOT one entry per
# condition: a patient can list 15 conditions and at most 3 timings, and the
# two counts agree in only 16% of rows, so it is a de-duplicated set of the
# timing categories that apply somewhere in the list. Per-condition timing
# therefore cannot be recovered. What it can do is exclude patients for whom
# NO listed condition predates enrollment; those are unambiguously not
# baseline comorbidity. The remainder are kept, and a minority of their
# conditions may postdate enrollment. Recorded in DATA_ISSUES.csv.
ROSTER_TIMING_COLUMN = "phys_comorbid_when"
ROSTER_BASELINE_TIMING = "on or before enrollment"
# Catch-all roster entries whose label merely lists examples. "Other, e.g.
# chronic sinusitis, chronic bronchitis" is chosen by 276 patients and means
# "some other condition", not bronchitis, so matching on the examples inside it
# would attribute a lung condition to all of them.
ROSTER_CATCH_ALL = r"^other[, ]|^other\s+(i{1,3}|current|chronic)\b"
ROSTER_PATTERNS = {
    "has_diabetes": r"diabetes",
    "has_hypertension": r"hypertension",
    "has_cardiac_disease": r"coronary|myocardial|heart failure|angina|arrhythmia|cardiovascular",
    "has_stroke": r"stroke|transient ischemic",
    "has_respiratory_disease": r"asthma|obstructive pulmonary|pulmonary|sleep apnea|bronchitis",
    "has_cancer": r"cancer",
    "has_musculoskeletal_disorder": r"arthritis|back|musculoskeletal|fibromyalgia|osteoporosis",
    "has_renal_disease": r"renal|kidney",
    "has_hyperlipidaemia": r"hyperlipidemia|hyperlipidaemia|cholesterol",
}

# Coarser columns, defined as "any of" the specific ones plus their own direct
# sources. ds_02 and ds_03 record a single undifferentiated "Cardiovascular
# Disease" flag, which is the coarse construct and cannot be split into cardiac
# and cerebrovascular after the fact, so it feeds only this column.
COARSE = {
    "has_cardiovascular_disease": {
        "from_columns": ["has_cardiac_disease", "has_stroke"],
        "own_sources": {
            "02_Aragones_2012": ["CARDIOVASC"],
            "03_Aragones_2019": ["CARDIOVASCULAR"],
        },
    },
}

# Each study counted a different menu of conditions, so these numbers are only
# interpretable within a study. Named accordingly, and never pooled as if they
# were on one scale. ds_15's cds2 is excluded: it is zero for all 65 patients,
# which is not a plausible count.
# ds_08 records up to 20 long-term conditions as Bayliss burden ratings, one
# column each, 0 meaning the patient does not have that condition. Its own
# codebook calls them "Unklar", but the paper cites Bayliss and reports "a mean
# of 6.2 (SD 3.0) long term conditions other than diabetes or heart disease".
# Counting ltc1..ltc20 above zero gives 7.49, and subtracting each patient's
# diabetes and heart-disease index conditions gives 6.35, which reproduces the
# published figure. That is what decodes the columns.
LTC_COLUMNS = [f"ltc{slot}" for slot in range(1, 21)]
LTC_STUDY = "08_Coventry_2015"

COUNT_SOURCES = {
    "03_Aragones_2019": "CHR_CONDITIONS",
    "14_Katon_1995": "cds2",
    "23_Rollman_2009": "LTCn_0",
    "24_Rollman_2016": "n_phys_comorbids",
    "25_Rollman_2017": "phys_comorbid_count",
    "31_Unützer_2002": "NUMDIS2",
    "32_Wells_2000": "CHRONDIS",
}
EXCLUDED_COUNTS = {
    "15_Katon_1996": "cds2 is 0 for all 65 patients, which cannot be a real condition count."
}

# Per-column overrides where one column in a study is coded unlike its siblings.
COLUMN_CODING = {
    # 0 absent, 1 and 2 both present. Its codebook gives no value labels, so
    # the magnitude is treated as an undocumented severity grade, not a count.
    ("23_Rollman_2009", "CHF_0"): "grade",
}

_TRUE = {"1", "1.0", "true", "yes"}
_FALSE = {"0", "0.0", "false", "no"}


def _read_presence(df: pd.DataFrame, study_id: str, column: str) -> pd.Series:
    """Read one raw column for one study as True/False/missing."""
    rows = df[COLNAME_STUDYID] == study_id
    raw = df.loc[rows, column]
    coding = COLUMN_CODING.get((study_id, column), CODING.get(study_id, "binary"))
    text = raw.astype("string").str.strip().str.lower()

    present = pd.Series(pd.NA, index=raw.index, dtype="boolean")
    undocumented = UNDOCUMENTED_CODES.get((study_id, column), set())
    if undocumented:
        numeric = pd.to_numeric(raw, errors="coerce")
        bad = numeric.isin(undocumented)
        if bad.any():
            logger.warning(
                f"{study_id} {column}: {int(bad.sum())} row(s) carry an undocumented "
                f"code {sorted(undocumented)} and are left missing."
            )
        text = text.where(~bad)

    if coding == "one_blank_no":
        # A blank is a real "no" here, so the column is never missing.
        present = pd.Series(False, index=raw.index, dtype="boolean")
        present.loc[text.isin(_TRUE)] = True
        if undocumented:
            numeric = pd.to_numeric(raw, errors="coerce")
            present = present.where(~numeric.isin(undocumented))
    elif coding == "grade":
        numeric = pd.to_numeric(raw, errors="raise")
        present = (numeric > 0).astype("boolean").where(numeric.notna())
    else:
        present.loc[text.isin(_TRUE)] = True
        present.loc[text.isin(_FALSE)] = False
        unmapped = text.notna() & ~text.isin(_TRUE | _FALSE)
        if unmapped.any():
            logger.warning(
                f"{study_id} {column}: {int(unmapped.sum())} value(s) are neither "
                "true nor false and are left missing."
            )
    return present


def _icd_presence(df: pd.DataFrame, study_id: str, pattern: str) -> pd.Series:
    """Presence of a condition family across a study's ICD-10 code slots."""
    rows = df[COLNAME_STUDYID] == study_id
    slots = [c for c in ICD_COLUMNS if c in df.columns]
    codes = df.loc[rows, slots].astype("string").apply(lambda s: s.str.upper().str.strip())
    joined = codes.apply(lambda row: " ".join(x for x in row if pd.notna(x)), axis=1)
    matched = joined.str.contains(pattern, regex=True, na=False).astype("boolean")
    # A row carrying no codes at all is one where the diagnosis list was not
    # recorded, which is missing rather than "no conditions". ds_12 records its
    # list once, on the baseline row, so the follow-up rows are empty by design
    # and must not read as negative.
    listed = df.loc[rows, slots].notna().any(axis=1)
    return matched.where(listed, pd.NA)


def _roster_vocabulary(df: pd.DataFrame, study_id: str) -> set[str]:
    """Every distinct condition name this study's roster actually offers."""
    listed = df.loc[df[COLNAME_STUDYID] == study_id, ROSTER_COLUMN].dropna()
    return {part.strip() for entry in listed for part in str(entry).split(";") if part.strip()}


def _roster_presence(df: pd.DataFrame, study_id: str, pattern: str, cluster: str) -> pd.Series:
    """Presence of a condition in a patient's roster of diagnoses.

    Returns all-missing when the roster has no category for this condition at
    all. A roster answers only the questions it asks: ds_24 lists 49 condition
    names and none of them is renal, so "no renal disease recorded" would be an
    answer the study never gave, not a negative finding.

    Patients whose timings are entirely after enrollment are excluded, since
    none of their listed conditions can be baseline. Timing cannot be resolved
    per condition (see ROSTER_TIMING_COLUMN), so the rest are read as listed.
    """
    rows = df[COLNAME_STUDYID] == study_id
    names = df.loc[rows, ROSTER_COLUMN].astype("string")

    vocabulary = _roster_vocabulary(df, study_id)
    offered = [
        term
        for term in vocabulary
        if re.search(pattern, term, re.IGNORECASE)
        and not re.search(ROSTER_CATCH_ALL, term, re.IGNORECASE)
    ]
    if not offered:
        logger.info(
            f"{cluster}/{study_id}: the roster offers no category matching this "
            f"condition, so the study is left missing rather than recorded as negative."
        )
        return pd.Series(pd.NA, index=names.index, dtype="boolean")
    logger.debug(f"{cluster}/{study_id}: roster terms matched -> {sorted(offered)}")

    timings = df.loc[rows, ROSTER_TIMING_COLUMN].astype("string").str.lower()

    def matches(listed: object) -> bool:
        if pd.isna(listed):
            return False
        for condition in str(listed).split(";"):
            condition = condition.strip()
            if re.search(ROSTER_CATCH_ALL, condition, re.IGNORECASE):
                continue
            if re.search(pattern, condition, re.IGNORECASE):
                return True
        return False

    matched = pd.Series([matches(x) for x in names], index=names.index)
    any_baseline = timings.str.contains(ROSTER_BASELINE_TIMING, na=False)
    answered = matched.where(any_baseline, False).astype("boolean")
    # A row with no roster entry is one where the list was not taken.
    return answered.where(names.notna(), pd.NA)


def _at_baseline(df: pd.DataFrame, values: pd.Series) -> pd.Series:
    """Carry each patient's month-0 value across all of their rows.

    Not ``broadcast_within_patient``, which takes the first non-null value in
    row order. Several studies re-administer the comorbidity form at every
    visit and the answers change: 192 of ds_05's 384 patients have more than
    one distinct value for CRF_DM across their visits. This is a baseline risk
    dimension, so the month-0 answer is the one that belongs here. Patients
    with no month-0 row fall back to their earliest recorded visit.
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


def _study_presence(df: pd.DataFrame, study_id: str, columns: list[str]) -> pd.Series:
    """Combine a study's columns for one condition: positive if any is positive.

    Missing only when the study answered none of them, so a study recording a
    myocardial infarction and a heart-failure diagnosis separately is positive
    for the cardiac umbrella if either is.
    """
    answers = pd.concat([_read_presence(df, study_id, column) for column in columns], axis=1)
    any_positive = answers.fillna(False).any(axis=1)
    none_answered = answers.isna().all(axis=1)
    return any_positive.astype("boolean").where(~none_answered, pd.NA)


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize the comorbidity cluster across all studies."""
    harmonized_df = df[ID_COLS].copy()

    for condition, per_study in SOURCES.items():
        values = pd.Series(pd.NA, index=df.index, dtype="boolean")
        for study_id, columns in per_study.items():
            checks.require_columns(df, study_id, columns, CLUSTER_KEY)
            rows = checks.require_rows(df, study_id, CLUSTER_KEY)
            values.loc[rows] = _study_presence(df, study_id, columns).loc[rows]
        for study_id, coding in CODING.items():
            rows = df[COLNAME_STUDYID] == study_id
            if not rows.any():
                continue
            if coding == "roster" and condition in ROSTER_PATTERNS:
                values.loc[rows] = _roster_presence(
                    df, study_id, ROSTER_PATTERNS[condition], CLUSTER_KEY
                )
            elif coding == "icd_codes" and condition in ICD_PATTERNS:
                values.loc[rows] = _icd_presence(df, study_id, ICD_PATTERNS[condition])
        resolved = _at_baseline(df, values).astype("boolean")
        checks.check_within_patient_constant(df, resolved, CLUSTER_KEY, condition)
        harmonized_df[condition] = resolved

    for coarse, spec in COARSE.items():
        parts = [harmonized_df[c] for c in spec["from_columns"]]
        own = pd.Series(pd.NA, index=df.index, dtype="boolean")
        for study_id, columns in spec["own_sources"].items():
            rows = df[COLNAME_STUDYID] == study_id
            own.loc[rows] = _study_presence(df, study_id, columns).loc[rows]
        answers = pd.concat(parts + [_at_baseline(df, own)], axis=1)
        any_positive = answers.fillna(False).any(axis=1)
        none_answered = answers.isna().all(axis=1)
        harmonized_df[coarse] = any_positive.astype("boolean").where(~none_answered, pd.NA)

    counts = pd.Series(pd.NA, index=df.index, dtype="Float64")
    ltc_rows = df[COLNAME_STUDYID] == LTC_STUDY
    if ltc_rows.any():
        ratings = df.loc[ltc_rows, LTC_COLUMNS].apply(pd.to_numeric, errors="coerce")
        counts.loc[ltc_rows] = (
            (ratings > 0).sum(axis=1).where(ratings.notna().any(axis=1)).astype("Float64")
        )
    for study_id, column in COUNT_SOURCES.items():
        rows = df[COLNAME_STUDYID] == study_id
        counts.loc[rows] = pd.to_numeric(df.loc[rows, column], errors="raise").astype("Float64")
    harmonized_df["n_chronic_conditions_reported"] = _at_baseline(df, counts).astype("Int64")

    return harmonized_df[ID_COLS + HARMONIZED_COLS]


# --- Cluster metadata -------------------------------------------------------

_TRANSFORM = (
    "Screened bottom-up from every raw column in the concatenated frame against a "
    "13-system condition vocabulary, then mapped per study through that study's own "
    "coding scheme (see CODING: binary, one_blank_no, grade, roster). A condition is "
    "positive when any of that study's columns for it is positive, and missing only "
    "when the study recorded none of them. Values are broadcast within patient, since "
    "these are baseline attributes. During-follow-up events, severity instruments and "
    "lab values are excluded; see the module docstring."
)

COLUMN_PROVENANCE = {
    condition: {
        "description": description,
        "transformation": _TRANSFORM,
        "source_columns": {study: ", ".join(cols) for study, cols in SOURCES[condition].items()},
    }
    for condition, description in {
        "has_diabetes": "Diabetes of any type recorded at baseline.",
        "has_hypertension": "Hypertension or high blood pressure recorded at baseline.",
        "has_cardiac_disease": (
            "Any cardiac condition: angina, myocardial infarction, heart failure, "
            "coronary artery disease, or a study's own undifferentiated heart disease."
        ),
        "has_myocardial_infarction": "A specific history of myocardial infarction.",
        "has_heart_failure": "A specific heart-failure diagnosis.",
        "has_stroke": "Stroke or transient ischaemic attack.",
        "has_respiratory_disease": "Asthma, COPD, or another chronic lung condition.",
        "has_cancer": "Current or past malignancy.",
        "has_musculoskeletal_disorder": (
            "Arthritis, osteoporosis, chronic back pain or another musculoskeletal condition."
        ),
        "has_renal_disease": "Chronic renal insufficiency or kidney disease.",
        "has_hyperlipidaemia": "Hyperlipidaemia or raised cholesterol recorded at baseline.",
    }.items()
}
COLUMN_PROVENANCE["has_cardiovascular_disease"] = {
    "description": (
        "Any cardiovascular disease: the cardiac conditions above together with "
        "cerebrovascular disease. Coarser than has_cardiac_disease on purpose, so that "
        "studies recording only an undifferentiated 'cardiovascular disease' flag can "
        "be pooled with those recording specific diagnoses."
    ),
    "transformation": _TRANSFORM,
    "source_columns": {
        **{
            s: ", ".join(c) for s, c in COARSE["has_cardiovascular_disease"]["own_sources"].items()
        },
        "derived_from": ", ".join(COARSE["has_cardiovascular_disease"]["from_columns"]),
    },
}
COLUMN_PROVENANCE["n_chronic_conditions_reported"] = {
    "description": (
        "The number of chronic conditions the study itself recorded. NOT comparable "
        "across studies: each counted a different menu, with observed ranges from 1-6 "
        "to 0-11, so a 3 in one study is not a 3 in another."
    ),
    "transformation": _TRANSFORM,
    "source_columns": COUNT_SOURCES,
    "excluded": EXCLUDED_COUNTS,
}


def _sources_by_study() -> dict[str, list[str]]:
    sources: dict[str, list[str]] = {}
    for per_study in SOURCES.values():
        for study, columns in per_study.items():
            sources.setdefault(study, []).extend(columns)
    for study, column in COUNT_SOURCES.items():
        sources.setdefault(study, []).append(column)
    sources.setdefault(LTC_STUDY, []).extend(LTC_COLUMNS)
    for study, coding in CODING.items():
        if coding == "roster":
            sources.setdefault(study, []).extend([ROSTER_COLUMN, ROSTER_TIMING_COLUMN])
        elif coding == "icd_codes":
            sources.setdefault(study, []).extend(ICD_COLUMNS)
    for spec in COARSE.values():
        for study, columns in spec["own_sources"].items():
            sources.setdefault(study, []).extend(columns)
    return {study: sorted(set(columns)) for study, columns in sources.items()}


CONSUMPTION = {
    "sources": _sources_by_study(),
    "superseded": {},
    "review": {
        "LTC_0": "ds_18: 'LTC baseline' and 'LTCsev_0' 'LTC severity baseline' in a study "
        "with no medical-history script at all. Genuinely unharmonized comorbidity data, "
        "left for a follow-up once the LTC checklist behind it is identified.",
        "HbA1c": "ds_30: a lab value, not a diabetes diagnosis. Thresholding it would be a "
        "clinical judgment this cluster does not make.",
        "lvef_lt45": "ds_09: severity of cardiac disease, not its presence.",
        "cds2": "ds_15: a condition count that is 0 for all 65 patients, so it cannot be "
        "real. Excluded from n_chronic_conditions_reported rather than pooled.",
    },
    "conditional_on": {},
}
