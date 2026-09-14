from loguru import logger
import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR

# Richards 2008 = a UK Phase II collaborative-care RCT (Psychological Medicine
# 2008;38:279-287). A patient-level RCT nested within a cluster-randomised
# trial: depressed primary-care patients allocated to collaborative care
# (case-manager-coordinated medication management + brief psychological
# treatment over ~3 months, mostly by telephone) vs a patient-randomised control
# vs a cluster-randomised control. N = 114 (41 intervention / 38 patient-control
# / 35 cluster-control). Primary outcome: PHQ-9 at 3 months.
#
# The raw file has just two assessments per patient -- baseline and one
# ~3-month follow-up -- encoded with a grab-bag of suffix conventions
# (``_0``/``_f2``, ``_baseline``/``_FU``, ``TOT``/``TOTFU``, ...). This loader
# stacks the two into long format.

_STUDY_DIR = RAW_DATASETS_DIR / "21_Richards_2008"

# harmonised stem -> (baseline column, 3-month follow-up column)
PAIRED_COLS = {
    "phq9_total": ("Depres_0", "Depres_f2"),  # DepresSev_Mes == HPQ9
    # Labelled "SCL90 subscale" in the source (a summed score, ~12-74 range) --
    # NOT the SCL-20 mean used by the Katon/Simon trials. Kept distinct;
    # PHQ-9 (``phq9_total``) is this trial's primary depression outcome.
    "scl_depression_summed_score": ("SCLTOT", "SCLTOTFU"),
    "phq9_severity_category": ("PHQ9categories", "PHQ9FUcategories"),
    "phq9_depressed": ("PHQ9depression_yesNo", "PHQ9depressionFU_yesno"),
    "scid_depression_diagnosis": ("SCID_Yesno", "SCID_Yesno_FU"),
    "eq5d_mobility": ("EQ5DMobility_baseline", "EQ5DMobility_FU"),
    "eq5d_self_care": ("EQ5DSelfCare_baseline", "EQ5DSelfCare_FU"),
    "eq5d_usual_activities": ("EQ5DUsualactivities_baseline", "EQ5DUsualactivities_FU"),
    "eq5d_pain": ("EQ5DPain_baseline", "EQ5DPain_FU"),
    "eq5d_mood": ("EQ5DMood_baseline", "EQ5DMood_FU"),
    "eq5d_value": ("EQ5Dvalue_baseline", "EQ5Dvalue_FU"),
    "core_om_total_mean": (
        "CORETOTALMEAN_baselinegreaterthan31itemscomplete",
        "CORETOTALMEAN_FUgreaterthan31itemscomplete",
    ),
    "core_om_function": ("COREMEAN_Function_baseline", "COREMEAN_Function_FU"),
    "core_om_symptoms": ("COREMEAN_Symptoms_baseline", "COREMEAN_Symptoms_FU"),
    "core_om_wellbeing": ("COREMEAN_Wellbeing_baseline", "COREMEAN_Wellbeing_FU"),
    "core_om_risk": ("COREMEAN_Risk_baseline", "COREMEAN_Risk_FU"),
    "core_om_cutoff": ("COREcutoffs_baseline", "COREcutoffs_FU"),
    "core_om_symptoms_of_depression": ("COREsympdepbaseline", "COREsympdepFU"),
}

FOLLOW_UP_MONTHS = {0: 0, 1: 3}  # tuple position -> months

# Constant trial-level metadata; dropped.
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


def load(file_path=_STUDY_DIR / "Richards 2008 CLEANED.sav") -> pd.DataFrame:
    df = pd.read_spss(file_path, convert_categoricals=False)
    # treat blank or whitespace-only strings as missing, before dtype inference
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True)
    df = df.drop(columns=[c for c in _METADATA_COLS if c in df.columns])

    missing_id = df["Origpat_id"].isna()
    if missing_id.any():
        logger.warning(f"Dropped {int(missing_id.sum())} rows with missing Origpat_id.")
        df = df.loc[~missing_id]

    # The source assigns id "ROTW23009" to two clearly different patients
    # (different age/sex/scores), so repeated ids are disambiguated positionally
    # rather than dropped -- these are two people sharing a key, not one patient
    # recorded twice.
    ids = df["Origpat_id"].astype("string")
    dup_mask = ids.duplicated(keep=False)
    if dup_mask.any():
        logger.warning(
            f"Disambiguated {int(dup_mask.sum())} rows sharing "
            f"{ids[dup_mask].nunique()} patient id(s): {sorted(ids[dup_mask].unique())}"
        )
    ids = ids.where(~dup_mask, ids + "__" + (ids.groupby(ids).cumcount() + 1).astype("string"))
    df = df.assign(patient_id=ids).drop(columns="Origpat_id")

    if absent := [c for pair in PAIRED_COLS.values() for c in pair if c not in df.columns]:
        logger.warning(f"Declared paired column(s) absent from the export: {absent}")

    paired_cols = {c for pair in PAIRED_COLS.values() for c in pair}
    # Everything else is carried on both rows. Besides the trial arm and
    # demographics these are baseline-only measures (``Medadh_0``,
    # ``Antidepress_dose``, ...) with no follow-up counterpart in the export;
    # they keep their "baseline" names, so a value on the 3-month row reads as
    # that patient's baseline figure, not a 3-month measurement.
    static_cols = [c for c in df.columns if c not in paired_cols and c != "patient_id"]

    frames = []
    for position, months in FOLLOW_UP_MONTHS.items():
        visit = df[["patient_id", *static_cols]].copy()
        visit.insert(1, "follow_up_months", months)
        for stem, pair in PAIRED_COLS.items():
            col = pair[position]
            if col in df.columns:
                visit[stem] = df[col]
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
