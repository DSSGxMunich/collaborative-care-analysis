import pandas as pd

from collaborative_care_analysis.config import COLNAME_STUDYID

# from collaborative_care_analysis.utils import map_with_check


def harmonize_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize outcome variables for Bekelman 2018."""

    harmonized_df = df[
        [
            COLNAME_STUDYID,
            "patient_id",  # identifier for patient and caregiver
            "follow_up_months",
            # PHQ-9, depression symptom
            "phqtotal",
            "phqtotalv2",  # alt version of PHQ9; 21 less values than phqtotal where at least one PHQ item is missing,
            # and 3 rows with a completely different score from phqtotal
            "phq01",
            "phq02",
            "phq03",
            "phq04",
            "phq05",
            "phq06",
            "phq07",
            "phq08",
            "phq09",
            "phq10",  # additional question: If you checked off any problems, how difficult have these problems made it for you to do your work, take care of things at home, or get along with other people?
            # GAD-7, anxiety symptom
            "gadtotal",
            "gad01",
            "gad02",
            "gad03",
            "gad04",
            "gad05",
            "gad06",
            "gad07",
            "gad08",  # additional question: If you checked off any problems, how difficult have these problems made it for you to do your work, take care of things at home, or get along with other people?
            # "ticstot", # telephone Interview for Cognitive Status (TICS) used for screening
            # "ticstotv2", # telephone Interview for Cognitive Status (TICS) used for screening
            # KCCQ, heart-failure-specific quality of life
            "kccqos",
            "kccqsf01a",
            "kccqsf01b",
            "kccqsf01c",
            "kccqsf02",
            "kccqsf03",
            "kccqsf04",
            "kccqsf05",
            "kccqsf06",
            "kccqsf07",
            "kccqsf08a",
            "kccqsf08b",
            "kccqsf08c",
            # Pain
            "pegmean",
            "peg01",
            "peg02",
            "peg03",
            # Fatigue
            "ftgtot",
            "ftg01",
            "ftg02",
            "ftg03",
            "ftg04",
            "ftg05",
            "ftg06",
            "ftg07",
            "ftg08",
            # Dyspnea
            "dysptot",
            "dysp01",
            "dysp02",
            "dysp03",
            "dyspmean",  # Dyspnea mean
        ]
    ].copy()

    harmonized_df = harmonized_df.rename(
        columns={
            "phqtotal": "phq9_total",
            "phqtotalv2": "phq9_total_v2",
            "gadtotal": "gad7_total",
            "kccqos": "kccq_overall",
            "pegmean": "peg_mean",
            "ftgtot": "fatigue_total",
            "dysptot": "dyspnea_total",
            "dyspmean": "dyspnea_mean",
        }
    )

    return harmonized_df
