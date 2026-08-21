import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    yes_no_map = {0: "no", 1: "yes"}

    # prior cardiac procedures
    harmonized_df["has_had_percutaneous_coronary_intervention"] = map_with_check(
        harmonized_df["crf_pci"], yes_no_map, "crf_pci"
    )
    harmonized_df["has_had_coronary_artery_bypass_graft"] = map_with_check(
        harmonized_df["crf_cabg"], yes_no_map, "crf_cabg"
    )

    # implanted cardiac devices
    harmonized_df["has_no_cardiac_device"] = map_with_check(
        harmonized_df["crf_devicenone"], yes_no_map, "crf_devicenone"
    )
    harmonized_df["has_pacemaker"] = map_with_check(
        harmonized_df["crf_pace"], yes_no_map, "crf_pace"
    )
    harmonized_df["has_biventricular_pacemaker"] = map_with_check(
        harmonized_df["crf_biv"], yes_no_map, "crf_biv"
    )
    harmonized_df["has_implantable_cardioverter_defibrillator"] = map_with_check(
        harmonized_df["crf_icd"], yes_no_map, "crf_icd"
    )
    harmonized_df["has_biventricular_icd"] = map_with_check(
        harmonized_df["crf_bivicd"], yes_no_map, "crf_bivicd"
    )

    # heart failure etiology
    # NOTE: crf_cad does NOT reproduce the paper's published "Ischemic cause"
    # counts in Table 2 (control 69/157, intervention 73/157) -- raw crf_cad
    # gives control 72/157, intervention 63/157, direction even reversed.
    # Flagging in case anyone downstream expects it to match the paper.
    harmonized_df["is_heart_failure_etiology_ischemic"] = map_with_check(
        harmonized_df["crf_cad"], yes_no_map, "crf_cad"
    )
    harmonized_df["is_heart_failure_etiology_hypertensive"] = map_with_check(
        harmonized_df["crf_ethtn"], yes_no_map, "crf_ethtn"
    )
    harmonized_df["is_heart_failure_etiology_valvular"] = map_with_check(
        harmonized_df["crf_etval"], yes_no_map, "crf_etval"
    )
    harmonized_df["is_heart_failure_etiology_alcohol_related"] = map_with_check(
        harmonized_df["crf_etalc"], yes_no_map, "crf_etalc"
    )
    harmonized_df["is_heart_failure_etiology_idiopathic_or_other"] = map_with_check(
        harmonized_df["crf_etidi"], yes_no_map, "crf_etidi"
    )

    # allergies, free text -- left as-is, just renamed
    harmonized_df = harmonized_df.rename(
        columns={"crf_allergies": "allergies_description"}, errors="raise"
    )

    # return the harmonized dataset which has only the values we want
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_had_percutaneous_coronary_intervention",
            "has_had_coronary_artery_bypass_graft",
            "has_no_cardiac_device",
            "has_pacemaker",
            "has_biventricular_pacemaker",
            "has_implantable_cardioverter_defibrillator",
            "has_biventricular_icd",
            "is_heart_failure_etiology_ischemic",
            "is_heart_failure_etiology_hypertensive",
            "is_heart_failure_etiology_valvular",
            "is_heart_failure_etiology_alcohol_related",
            "is_heart_failure_etiology_idiopathic_or_other",
            "allergies_description",
        ]
    ]
