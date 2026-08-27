import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

ID_COLS = [
    COLNAME_STUDYID,
    "patient_id",
    "follow_up_months",
]

KEEP_COLS = [
    "mhses_total",
    "phqdep_syndrome",
]


RENAME_MAP = {
    # PHQ-9 items
    "phq2wk_noint": "phq01",
    "phq2wk_down": "phq02",
    "phq2wk_sleep": "phq03",
    "phq2wk_energy": "phq04",
    "phq2wk_eat": "phq05",
    "phq2wk_bad": "phq06",
    "phq2wk_conc": "phq07",
    "phq2wk_speed": "phq08",
    "phq2wk_dead": "phq09",

    # PHQ-9 derived measures
    "phqdep_total": "phq9_total",
    "phqdep_total1": "phq9_symptom_count",
    "phqdep_total_impute": "phq9_total_imputed",
    "phqdep_syndrome_2grp": "phq9_syndrome_2grp", # Major depressive symptoms
    "phqdep_miss": "phq9_missing_items",
    "phqdep_severity": "phq9_severity",

    # GAD-7 items
    **{f"gad{i}": f"gad{i:02d}" for i in range(1, 8)},
    # GAD-7 derived measures
    "gad_2grp": "gad7_2grp",
    "gad_total": "gad7_total",
    "gad_severity": "gad7_severity",
    "gad_total_miss": "gad7_missing_items",
    "gad_severity_imp": "gad7_severity_imputed",
    "gad_total_impute": "gad7_total_imputed",

    # AQoL-8D items
    **{f"aqol{i}": f"aqol{i:02d}" for i in range(1, 36)},
    # AQoL-8D dimensions
    "vIL": "aqol8d_independent_living",
    "vHap": "aqol8d_happiness",
    "vMH": "aqol8d_mental_health",
    "vCop": "aqol8d_coping",
    "vRel": "aqol8d_relationships",
    "vSW": "aqol8d_self_worth",
    "vPa": "aqol8d_pain",
    "vS": "aqol8d_senses",
    "AQoL8DUtility": "aqol8d_utility",

    # Mental Health Self-Efficacy Scale
    **{f"mhses{i}": f"mhses{i:02d}" for i in range(1, 7)},
    "mhses_total_miss": "mhses_missing_items",
    "mhses_total_impute": "mhses_total_imputed",

}

OUTCOME_COLS = ID_COLS + list(RENAME_MAP) + KEEP_COLS

def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Fletcher 2021b."""

    harmonized_df = df[OUTCOME_COLS].copy()

    return harmonized_df.rename(
        columns=RENAME_MAP,
        errors="raise",
    )