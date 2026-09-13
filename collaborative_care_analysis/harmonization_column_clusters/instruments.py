"""Cluster: the repeated depression and anxiety measurement instruments.

Each instrument keeps its **native scale**. There is no merged
``depression_severity`` column, no cross-walk between instruments, and no
within-study standardisation: the studies split into instrument families that
are analysed separately, so nothing here has to put a PHQ-9 sum and an SCL-20
mean on one axis. Six families appear across the 30 studies, and only two of
them are multi-study:

* **PHQ-9** (9 items, summed, 0-27) in 15 studies
* **SCL-20** (mean of the 20 SCL-90 depression items, 0-4) in 10 studies
* HSCL (ds_03), BDI (ds_09), CIS-R (ds_20), HRSD-17 (ds_23) and a 23-item
  CES-D (ds_32) in one study each

No study administered two families, so the two networks are disjoint.

EQ-5D, SF-12/36, KCCQ and WHODAS are deliberately **not** here: they are
health-status instruments and belong with the quality-of-life cluster that
derives from them.

Scoring rules, applied uniformly:

* Where a study ships its own total, that total is used, and it is checked
  against the sum of its items at build time rather than trusted blindly.
* Where no total ships, it is computed from the items and **every** item must
  be present (``min_count``); a partial item set yields NA rather than a
  silently low score. This follows ``harmonization_outcomes/ds_13``.
* The PHQ-9 "difficulty" item and the GAD-7 equivalent measure functional
  impairment, not symptom severity, and are never added to the total. They get
  their own columns.
"""

from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID
from collaborative_care_analysis.harmonization_column_clusters.concat import ID_COLS

CLUSTER_KEY = "instruments"

PHQ9_ITEMS = [f"phq9_{i}" for i in range(1, 10)]
GAD7_ITEMS = [f"gad7_{i}" for i in range(1, 8)]
HARMONIZED_COLS = (
    PHQ9_ITEMS
    + ["phq9_total", "phq9_difficulty"]
    + GAD7_ITEMS
    + ["gad7_total", "gad7_difficulty"]
    + ["scl20_mean", "hscl_total", "bdi_total", "cisr_total", "hrsd17_total", "cesd23_total"]
)

# Item responses are 0-3 on both instruments ("not at all" to "nearly every
# day"). Anything outside that is a coding error, not a real response.
ITEM_RANGE = (0, 3)
PHQ9_TOTAL_RANGE = (0, 27)
GAD7_TOTAL_RANGE = (0, 21)
SCL20_RANGE = (0, 4)

# Per-study PHQ-9 items, keyed by item number so a study contributing only some
# items (ds_02 and ds_22 carry the suicidality item alone) needs no special case.
PHQ9_ITEM_COLUMNS: dict[str, dict[int, str]] = {
    "02_Aragones_2012": {9: "phq9_9"},
    "04_Bekelman_2018": {i: f"phq0{i}" for i in range(1, 10)},
    "05_Bekelman_2015": {i: f"PHQ0{i}" for i in range(1, 10)},
    "08_Coventry_2015": {i: f"phq{i}" for i in range(1, 10)},
    # Named by content rather than number. The mapping to item positions is not
    # read off the names: `phqdep_total` equals the sum of these nine in this
    # order on all 4,680 rows where both exist, which fixes the order.
    "10_Fletcher_2021a": dict(
        enumerate(
            [
                "phq2wk_noint",
                "phq2wk_down",
                "phq2wk_sleep",
                "phq2wk_energy",
                "phq2wk_eat",
                "phq2wk_bad",
                "phq2wk_conc",
                "phq2wk_speed",
                "phq2wk_dead",
            ],
            start=1,
        )
    ),
    # Same instrument and the same content names as ds_10. This study asked the
    # PHQ-9 twice per wave on different forms: these unsuffixed columns hold the
    # 3- and 12-month waves, and the `_t` toolkit form holds baseline (see
    # PHQ9_BASELINE_ITEM_COLUMNS).
    "11_Fletcher_2021b": dict(
        enumerate(
            [
                "phq2wk_noint",
                "phq2wk_down",
                "phq2wk_sleep",
                "phq2wk_energy",
                "phq2wk_eat",
                "phq2wk_bad",
                "phq2wk_conc",
                "phq2wk_speed",
                "phq2wk_dead",
            ],
            start=1,
        )
    ),
    "12_Gensichen_2009": {i: f"phqf{i}" for i in range(1, 10)},
    "13_Hölzel_2018": {i: f"PHQ9_{i}" for i in range(1, 10)},
    "22_Richards_2013": {9: "phq9_q9"},
    "30_Srinivasan_2022": {i: f"phq{i}" for i in range(1, 10)},
}

# Totals the study ships itself. Studies absent here have their total computed
# from the items above (ds_08, ds_11, ds_12).
PHQ9_TOTAL_COLUMNS: dict[str, str] = {
    "02_Aragones_2012": "phq9_total",
    # phqtotalv2, not phqtotal: v2 equals the item sum on all 982 rows, while
    # phqtotal disagrees on 3 and scores 21 further rows from incomplete items.
    "04_Bekelman_2018": "phqtotalv2",
    "05_Bekelman_2015": "PHQSCORE",
    "10_Fletcher_2021a": "phqdep_total",
    "13_Hölzel_2018": "PHQ_Summe",
    "21_Richards_2008": "phq9_total",
    "22_Richards_2013": "phq9_total",
    "24_Rollman_2016": "phq9_total",
    "25_Rollman_2017": "phq9_total",
    "26_Salisbury_2016": "phq9_total",
    # Named `depression`, but it equals the sum of phq1..phq9 on all 7,680 rows.
    "30_Srinivasan_2022": "depression",
    # Named `Depression_severity`. This study's own measure field (DepresSev_Mes)
    # reads "HPQ9", a typo for PHQ-9 already noted in the loader audit.
    "33_Zimmerman_2016": "Depression_severity",
}

# Items recorded on a different form at baseline. ds_11 carries its month-0
# PHQ-9 in `_t` (toolkit form) columns and its 3/12-month waves in the
# unsuffixed ones, so neither set alone covers the study: the `_t` columns are
# populated for 1,868 baseline rows and empty afterwards, the unsuffixed ones
# for 2,361 follow-up rows and empty at baseline. Same shape as ds_09's BDI.
PHQ9_BASELINE_ITEM_COLUMNS: dict[str, dict[int, str]] = {
    "11_Fletcher_2021b": {
        i: column + "_t" for i, column in PHQ9_ITEM_COLUMNS["11_Fletcher_2021b"].items()
    },
}

# The 10th PHQ-9 question ("how difficult have these problems made it ...").
PHQ9_DIFFICULTY_COLUMNS: dict[str, str] = {
    "04_Bekelman_2018": "phq10",
    "05_Bekelman_2015": "PHQ10",
    "30_Srinivasan_2022": "phq10",
}

GAD7_ITEM_COLUMNS: dict[str, dict[int, str]] = {
    "04_Bekelman_2018": {i: f"gad0{i}" for i in range(1, 8)},
    "05_Bekelman_2015": {i: f"GAD0{i}" for i in range(1, 8)},
    "08_Coventry_2015": {i: f"gad{i}" for i in range(1, 8)},
    "11_Fletcher_2021b": {i: f"gad{i}" for i in range(1, 8)},
    "13_Hölzel_2018": {i: f"GAD7_{i}" for i in range(1, 8)},
    "30_Srinivasan_2022": {i: f"gad{i}" for i in range(1, 8)},
}

GAD7_TOTAL_COLUMNS: dict[str, str] = {
    "04_Bekelman_2018": "gadtotal",
    # gad_total, not gad_total_impute: the imputed variant adds 7 rows and never
    # disagrees elsewhere, but imputed values should not enter a harmonized
    # column unlabelled.
    "10_Fletcher_2021a": "gad_total",
    "11_Fletcher_2021b": "gad_total",
    "26_Salisbury_2016": "gad7_total",
    # Named `anxiety`; equals the sum of gad1..gad7 on all 7,680 rows.
    "30_Srinivasan_2022": "anxiety",
}

GAD7_DIFFICULTY_COLUMNS: dict[str, str] = {"04_Bekelman_2018": "gad08"}

# ds_22 Richards 2013 is deliberately absent from GAD7_TOTAL_COLUMNS. Its
# `gad7_total` is an integer 0-26, and 211 of its 1,822 values exceed 21, the
# most a GAD-7 can score. The excess appears at every wave including baseline,
# so it is not an artifact of the loader stacking the 36-month wave's
# differently-named column. The study ships no GAD-7 items, so the scale cannot
# be recovered from the data, and its codebook says only "Generalised Anxiety
# Disorder Total score". Pooling it with true 0-21 totals would put two scales
# in one column, so it is left out until the paper or the study team settles
# what was administered. Its PHQ-9 is unaffected and is used.
GAD7_SCALE_UNRESOLVED = {
    "22_Richards_2013": "gad7_total values run 0-26; GAD-7 maxes at 21 and no items ship."
}

# Every SCL-20 study's loader already emits this name. ds_29 has it in its
# export but no harmonization script, so it is absent from the merged dataset
# today and reaches the pooled data only through this cluster.
SCL20_STUDIES = [
    "14_Katon_1995",
    "15_Katon_1996",
    "16_Katon_1999",
    "17_Katon_2001",
    "18_Katon_2004",
    "19_Katon_2010",
    "27_Simon_2000",
    "28_Simon_2004",
    "29_Simon_2011",
    "31_Unützer_2002",
]

# One study each, so nothing to reconcile across studies: taken as shipped.
SINGLE_STUDY_TOTALS: dict[str, tuple[str, str]] = {
    "hscl_total": ("03_Aragones_2019", "HSCLTOT"),
    "cisr_total": ("20_Patel_2010", "CISRTot"),
    "hrsd17_total": ("23_Rollman_2009", "hrsd17_total"),
    "cesd23_total": ("32_Wells_2000", "NWCESD"),
}

# ds_09 splits its BDI across two columns: the enrolment screening score at
# baseline and the repeated measure at 2/4/6 months. Same rule as
# harmonization_outcomes/ds_09.
BDI_STUDY = "09_Davidson_2013"
BDI_BASELINE_COLUMN = "bdiscore_01"
BDI_FOLLOW_UP_COLUMN = "bdiscore"


def _numeric(df: pd.DataFrame, study_rows: pd.Series, column: str) -> pd.Series:
    """Read one raw column for one study as numbers, failing on junk."""
    return pd.to_numeric(df.loc[study_rows, column], errors="raise")


def _in_range(values: pd.Series, bounds: tuple[int, int], what: str) -> pd.Series:
    """Null out values outside an instrument's defined range, and say so."""
    outside = values.notna() & ~values.between(*bounds)
    if outside.any():
        logger.warning(f"{what}: {int(outside.sum())} value(s) outside {bounds} set to missing.")
    return values.where(~outside)


def _whole_numbers(values: pd.Series, what: str) -> pd.Series:
    """Null out non-integer scores on instruments scored as sums of integer items.

    A PHQ-9 or GAD-7 total is a sum of 0-3 items, so a fractional value is a
    prorated or mis-entered score rather than a possible one. ds_26 ships two
    such PHQ-9 totals and no items to recompute them from.
    """
    fractional = values.notna() & (values % 1 != 0)
    if fractional.any():
        logger.warning(f"{what}: {int(fractional.sum())} non-integer score(s) set to missing.")
    return values.where(~fractional)


def _collect_items(
    df: pd.DataFrame,
    item_columns: dict[str, dict[int, str]],
    names: list[str],
    baseline_columns: dict[str, dict[int, str]] | None = None,
) -> pd.DataFrame:
    """Assemble per-item columns across studies, on the instrument's own scale.

    ``baseline_columns`` overlays a study that recorded the same items on a
    different form at month 0, so both waves reach the same harmonized items.
    """
    items = pd.DataFrame(index=df.index, columns=names, dtype="float64")
    for study_id, per_item in item_columns.items():
        study_rows = df[COLNAME_STUDYID] == study_id
        for number, column in per_item.items():
            values = _in_range(
                _numeric(df, study_rows, column), ITEM_RANGE, f"{study_id} {column}"
            )
            items.loc[study_rows, names[number - 1]] = values
    for study_id, per_item in (baseline_columns or {}).items():
        baseline_rows = (df[COLNAME_STUDYID] == study_id) & (df["follow_up_months"] == 0)
        for number, column in per_item.items():
            values = _in_range(
                _numeric(df, baseline_rows, column), ITEM_RANGE, f"{study_id} {column}"
            )
            items.loc[baseline_rows, names[number - 1]] = values
    return items


def _total_from_items(items: pd.DataFrame, names: list[str]) -> pd.Series:
    """Sum items, requiring every one of them: a partial set yields NA."""
    return items[names].sum(axis=1, min_count=len(names))


def _apply_shipped_totals(
    df: pd.DataFrame,
    total: pd.Series,
    computed: pd.Series,
    total_columns: dict[str, str],
    bounds: tuple[int, int],
    label: str,
) -> pd.Series:
    """Overlay each study's own total, warning where it contradicts its items."""
    for study_id, column in total_columns.items():
        study_rows = df[COLNAME_STUDYID] == study_id
        shipped = _whole_numbers(
            _in_range(_numeric(df, study_rows, column), bounds, f"{study_id} {column}"),
            f"{study_id} {column}",
        )
        both = shipped.notna() & computed.loc[study_rows].notna()
        if both.any():
            disagree = int((shipped[both] != computed.loc[study_rows][both]).sum())
            if disagree:
                logger.warning(
                    f"{study_id}: {label} column {column!r} disagrees with the sum of "
                    f"its items on {disagree} row(s); the study's own total is kept."
                )
        total.loc[study_rows] = shipped
    return total


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize the instruments cluster across all studies."""
    harmonized_df = df[ID_COLS].copy()

    phq9 = _collect_items(df, PHQ9_ITEM_COLUMNS, PHQ9_ITEMS, PHQ9_BASELINE_ITEM_COLUMNS)
    gad7 = _collect_items(df, GAD7_ITEM_COLUMNS, GAD7_ITEMS)

    phq9_from_items = _total_from_items(phq9, PHQ9_ITEMS)
    gad7_from_items = _total_from_items(gad7, GAD7_ITEMS)
    phq9_total = _apply_shipped_totals(
        df,
        phq9_from_items.copy(),
        phq9_from_items,
        PHQ9_TOTAL_COLUMNS,
        PHQ9_TOTAL_RANGE,
        "PHQ-9 total",
    )
    gad7_total = _apply_shipped_totals(
        df,
        gad7_from_items.copy(),
        gad7_from_items,
        GAD7_TOTAL_COLUMNS,
        GAD7_TOTAL_RANGE,
        "GAD-7 total",
    )

    for name in PHQ9_ITEMS:
        harmonized_df[name] = phq9[name].astype("Int64")
    harmonized_df["phq9_total"] = phq9_total.astype("Int64")
    harmonized_df["phq9_difficulty"] = _single_item(df, PHQ9_DIFFICULTY_COLUMNS)
    for name in GAD7_ITEMS:
        harmonized_df[name] = gad7[name].astype("Int64")
    harmonized_df["gad7_total"] = gad7_total.astype("Int64")
    harmonized_df["gad7_difficulty"] = _single_item(df, GAD7_DIFFICULTY_COLUMNS)

    scl20 = pd.Series(pd.NA, index=df.index, dtype="Float64")
    for study_id in SCL20_STUDIES:
        study_rows = df[COLNAME_STUDYID] == study_id
        scl20.loc[study_rows] = _in_range(
            _numeric(df, study_rows, "scl20_mean"), SCL20_RANGE, f"{study_id} scl20_mean"
        ).astype("Float64")
    harmonized_df["scl20_mean"] = scl20

    for name, (study_id, column) in SINGLE_STUDY_TOTALS.items():
        values = pd.Series(pd.NA, index=df.index, dtype="Float64")
        study_rows = df[COLNAME_STUDYID] == study_id
        values.loc[study_rows] = _numeric(df, study_rows, column).astype("Float64")
        harmonized_df[name] = values

    harmonized_df["bdi_total"] = _bdi_total(df)

    return harmonized_df[ID_COLS + HARMONIZED_COLS]


def _single_item(df: pd.DataFrame, columns: dict[str, str]) -> pd.Series:
    """One 0-3 item read per study, for the two functional-difficulty questions."""
    values = pd.Series(pd.NA, index=df.index, dtype="Float64")
    for study_id, column in columns.items():
        study_rows = df[COLNAME_STUDYID] == study_id
        values.loc[study_rows] = _in_range(
            _numeric(df, study_rows, column), ITEM_RANGE, f"{study_id} {column}"
        ).astype("Float64")
    return values.astype("Int64")


def _bdi_total(df: pd.DataFrame) -> pd.Series:
    """ds_09's BDI: the screening score at baseline, the repeated measure after."""
    values = pd.Series(pd.NA, index=df.index, dtype="Float64")
    study_rows = df[COLNAME_STUDYID] == BDI_STUDY
    if not study_rows.any():
        return values.astype("Int64")
    follow_up = _numeric(df, study_rows, BDI_FOLLOW_UP_COLUMN)
    baseline = _numeric(df, study_rows, BDI_BASELINE_COLUMN)
    is_baseline = df.loc[study_rows, "follow_up_months"] == 0
    values.loc[study_rows] = follow_up.mask(is_baseline, baseline).astype("Float64")
    return values.astype("Int64")


# --- Cluster metadata -------------------------------------------------------

_SCALES = {
    "phq9_total": "PHQ-9, sum of 9 items, 0-27.",
    "gad7_total": "GAD-7, sum of 7 items, 0-21.",
    "scl20_mean": "SCL-20, mean of the 20 SCL-90 depression items, 0-4.",
    "hscl_total": "Hopkins Symptom Checklist total (ds_03 only).",
    "bdi_total": "Beck Depression Inventory total, 0-63 (ds_09 only).",
    "cisr_total": "Clinical Interview Schedule-Revised total (ds_20 only).",
    "hrsd17_total": "Hamilton Rating Scale for Depression, 17-item (ds_23 only).",
    "cesd23_total": "CES-D, 23-item variant (ds_32 only).",
}

_TRANSFORM = (
    "Taken on the instrument's native scale; no cross-walk between instruments and "
    "no standardisation. Where the study ships its own total it is used, after being "
    "checked against the sum of its items; otherwise the total is computed from the "
    "items and every item must be present, so a partial set yields missing rather "
    "than a falsely low score. Values outside the instrument's defined range are set "
    "missing. The functional-difficulty questions are kept separate from the totals."
)

COLUMN_PROVENANCE = {
    **{
        name: {
            "description": f"PHQ-9 item {i} (0-3).",
            "transformation": _TRANSFORM,
            "source_columns": {
                study: per_item[i]
                for study, per_item in PHQ9_ITEM_COLUMNS.items()
                if i in per_item
            },
        }
        for i, name in enumerate(PHQ9_ITEMS, start=1)
    },
    **{
        name: {
            "description": f"GAD-7 item {i} (0-3).",
            "transformation": _TRANSFORM,
            "source_columns": {
                study: per_item[i]
                for study, per_item in GAD7_ITEM_COLUMNS.items()
                if i in per_item
            },
        }
        for i, name in enumerate(GAD7_ITEMS, start=1)
    },
    "phq9_total": {
        "description": _SCALES["phq9_total"],
        "transformation": _TRANSFORM,
        "source_columns": PHQ9_TOTAL_COLUMNS,
        "computed_from_items": ["08_Coventry_2015", "11_Fletcher_2021b", "12_Gensichen_2009"],
    },
    "gad7_total": {
        "description": _SCALES["gad7_total"],
        "transformation": _TRANSFORM,
        "source_columns": GAD7_TOTAL_COLUMNS,
        "computed_from_items": ["05_Bekelman_2015", "08_Coventry_2015", "13_Hölzel_2018"],
    },
    "phq9_difficulty": {
        "description": "PHQ-9 functional-difficulty question (0-3); never part of the total.",
        "transformation": _TRANSFORM,
        "source_columns": PHQ9_DIFFICULTY_COLUMNS,
    },
    "gad7_difficulty": {
        "description": "GAD-7 functional-difficulty question (0-3); never part of the total.",
        "transformation": _TRANSFORM,
        "source_columns": GAD7_DIFFICULTY_COLUMNS,
    },
    "scl20_mean": {
        "description": _SCALES["scl20_mean"],
        "transformation": _TRANSFORM,
        "source_columns": {study: "scl20_mean" for study in SCL20_STUDIES},
    },
    **{
        name: {
            "description": _SCALES[name],
            "transformation": _TRANSFORM,
            "source_columns": {study: column},
        }
        for name, (study, column) in SINGLE_STUDY_TOTALS.items()
    },
    "bdi_total": {
        "description": _SCALES["bdi_total"],
        "transformation": (
            "ds_09 records the enrolment screening BDI and the repeated 2/4/6-month "
            "measure in separate columns, so the baseline row takes the screening "
            "score and later rows the repeated one. " + _TRANSFORM
        ),
        "source_columns": {BDI_STUDY: [BDI_BASELINE_COLUMN, BDI_FOLLOW_UP_COLUMN]},
    },
}


def _sources_by_study() -> dict[str, list[str]]:
    """Every raw column this cluster reads, grouped by study."""
    sources: dict[str, list[str]] = {}
    for mapping in (PHQ9_ITEM_COLUMNS, PHQ9_BASELINE_ITEM_COLUMNS, GAD7_ITEM_COLUMNS):
        for study, per_item in mapping.items():
            sources.setdefault(study, []).extend(per_item.values())
    for mapping in (
        PHQ9_TOTAL_COLUMNS,
        GAD7_TOTAL_COLUMNS,
        PHQ9_DIFFICULTY_COLUMNS,
        GAD7_DIFFICULTY_COLUMNS,
    ):
        for study, column in mapping.items():
            sources.setdefault(study, []).append(column)
    for study in SCL20_STUDIES:
        sources.setdefault(study, []).append("scl20_mean")
    for study, column in SINGLE_STUDY_TOTALS.values():
        sources.setdefault(study, []).append(column)
    sources.setdefault(BDI_STUDY, []).extend([BDI_BASELINE_COLUMN, BDI_FOLLOW_UP_COLUMN])
    return {study: sorted(set(columns)) for study, columns in sources.items()}


CONSUMPTION = {
    "sources": _sources_by_study(),
    "superseded": {
        "phqtotal": "ds_04: the study's earlier PHQ-9 total. It disagrees with the sum "
        "of its own items on 3 rows and scores 21 further rows from an incomplete item "
        "set; phqtotalv2 matches the items exactly and is used instead.",
        "gad_total_impute": "ds_10: gad_total with 7 imputed values added. It never "
        "disagrees where both exist, but imputed values should not enter a harmonized "
        "column unlabelled.",
        "ZDepression_severity": "ds_33: Depression_severity already standardised within "
        "this study (mean 0, sd 1). Instruments are kept on their native scale, so the "
        "unstandardised column is used and this one carries no extra information.",
    },
    "review": {
        "gad7_total": "ds_22: an anxiety total on an unresolved scale (0-26 against a "
        "GAD-7 maximum of 21, at every wave). Kept in the frame rather than dropped, "
        "and deliberately not pooled into the harmonized gad7_total.",
        "DepresSev_Mes": "ds_33: names the instrument used ('HPQ9', a typo for PHQ-9) "
        "rather than measuring anything. It is the evidence that Depression_severity is "
        "a PHQ-9 total, so it is kept rather than dropped.",
    },
    "conditional_on": {},
}
