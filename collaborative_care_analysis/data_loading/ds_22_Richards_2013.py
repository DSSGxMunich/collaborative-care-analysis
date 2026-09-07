import re

import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Richards 2013 = the CADET trial (BMJ 2013;347:f4913). Cluster RCT, 51 UK
# general practices, N = 581 adults with depression (PHQ-9 >= 10). Collaborative
# care (a care manager delivering low-intensity psychological support + liaison
# with the GP, ~6-12 sessions) vs usual care. PHQ-9 assessed at baseline, 4, 12
# and 36 months; primary endpoint at 4 months.
#
# ``Richards 2013 CLEANED.sav`` (581 rows, unique ``Origpat_id``) already
# contains every timepoint: ``Depres_0/_f2/_f5/_f8`` are the PHQ-9 totals at
# 0/4/12/36 months, and the questionnaire item columns carry a
# ``Baseline_/FourMonth_/TwelveMonth_/ThirtySixMonth_`` prefix. This loader
# reshapes that single file to long -- no cross-file merge is needed (the old
# loader's merge with the 36-month file was redundant).

_STUDY_DIR = RAW_DATASETS_DIR / "22_Richards_2013"

PREFIX_TO_MONTHS = {
    "baseline_": 0,
    "fourmonth_": 4,
    "twelvemonth_": 12,
    "thirtysixmonth_": 36,
}

# ``Depres_``/``Medadh_`` use a numeric follow-up suffix instead of a prefix.
SUFFIX_TO_MONTHS = {"_0": 0, "_f2": 4, "_f5": 12, "_f8": 36}
SUFFIXED_STEMS = {"Depres": "phq9_total", "Medadh": "medication_adherence"}

TIME_INDEPENDENT_COLS = [
    "Group",
    "Cluster_random",
    "Age",
    "Sex",
    "LTC_0",
    "LTCn_0",
    "CSQ8_Total",
    "CESDsuicidality_0",
]

_METADATA_COLS = {
    "TriaI_id",
    "Time",
    "DepresSev_Mes",
    "DepresD_Mes",
    "LTC_Mes",
    "LTC_incl",
    "LTC_inclType",
    "LTC_emp",
    "Medadh_Mes",
    "Satcare_Mes",
    "Compl_Mes",
}

_PREFIX_RE = re.compile("^(" + "|".join(PREFIX_TO_MONTHS) + ")", re.IGNORECASE)


def _normalise_stem(stem: str) -> str:
    stem = stem.lower()
    # The 36-month file/columns call the GAD-7 total "gad_total"; every other
    # wave calls it "gad7_total". Normalise so the waves stack together.
    return stem.replace("gad_total", "gad7_total").replace("phq_total", "phq9_total")


def load() -> pd.DataFrame:
    df = pd.read_spss(_STUDY_DIR / "Richards 2013 CLEANED.sav", convert_categoricals=False)
    df = df.drop(columns=[c for c in _METADATA_COLS if c in df.columns]).convert_dtypes()
    df = df.rename(columns={"Origpat_id": "patient_id"}, errors="raise")
    df["patient_id"] = df["patient_id"].astype("string").str.strip()

    assert df["patient_id"].notna().all(), "Rows with missing patient_id"
    if df["patient_id"].duplicated().any():
        raise ValueError("Duplicate patient IDs in wide dataset")

    static_present = [c for c in TIME_INDEPENDENT_COLS if c in df.columns]
    comorbidity_cols = [c for c in df.columns if c.startswith("Com_") and c.endswith("_HaveIt")]
    static_cols = ["patient_id", *static_present, *comorbidity_cols]

    # (stem, months) -> raw column
    time_varying: dict[tuple[str, int], str] = {}
    unaccounted = []
    for col in df.columns:
        if col in static_cols:
            continue
        matched = False
        prefix_match = _PREFIX_RE.match(col)
        if prefix_match:
            months = PREFIX_TO_MONTHS[prefix_match.group(1).lower()]
            stem = _normalise_stem(col[prefix_match.end() :])
            time_varying[(stem, months)] = col
            matched = True
        else:
            for raw_stem, harmon_stem in SUFFIXED_STEMS.items():
                for suffix, months in SUFFIX_TO_MONTHS.items():
                    if col == f"{raw_stem}{suffix}":
                        time_varying[(harmon_stem, months)] = col
                        matched = True
        if not matched:
            unaccounted.append(col)

    if unaccounted:
        raise ValueError(f"Columns with no recognised timepoint marker: {sorted(unaccounted)}")

    all_months = sorted(set(PREFIX_TO_MONTHS.values()))
    frames = []
    for months in all_months:
        renames = {col: stem for (stem, m), col in time_varying.items() if m == months}
        visit = df[static_cols + list(renames)].rename(columns=renames)
        visit.insert(1, "follow_up_months", months)
        frames.append(visit)

    long = (
        pd.concat(frames, ignore_index=True, sort=False)
        .sort_values(["patient_id", "follow_up_months"], kind="stable")
        .reset_index(drop=True)
    )

    if long.duplicated(["patient_id", "follow_up_months"]).any():
        raise ValueError("Duplicate patient/time-point combinations")

    head = ["patient_id", "follow_up_months"]
    return long[head + [c for c in long.columns if c not in head]].convert_dtypes()
