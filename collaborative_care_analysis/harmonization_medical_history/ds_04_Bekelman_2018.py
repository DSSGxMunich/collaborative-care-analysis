import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    harmonized_df.rename(columns={"ticstot": "tics_total"}, inplace=True, errors="raise")

    # Max points per item, per codebook.
    tics_max = {
        "tics01": 2,
        "tics02": 5,
        "tics03": 5,
        "tics04": 2,
        "tics05": 10,
        "tics06": 5,
        "tics07": 4,
        "tics08": 2,
        "tics09": 2,
        "tics10": 2,
        "tics11": 2,
    }
    tics_total_max = 41
    tics_cols = list(tics_max) + ["tics_total"]

    # tics items should be numeric
    non_numeric = [c for c in tics_cols if not pd.api.types.is_numeric_dtype(harmonized_df[c])]
    assert not non_numeric, f"Non-numeric tics columns: {non_numeric}"

    # Each item score must fall within [0, max_points]
    for col, max_points in tics_max.items():
        out_of_range = harmonized_df[col].dropna()
        bad = out_of_range[(out_of_range < 0) | (out_of_range > max_points)]
        assert bad.empty, f"{col} has values outside [0, {max_points}]: {bad.unique()}"

    total_out_of_range = harmonized_df["tics_total"].dropna()
    bad_total = total_out_of_range[
        (total_out_of_range < 0) | (total_out_of_range > tics_total_max)
    ]
    assert bad_total.empty, (
        f"tics_total has values outside [0, {tics_total_max}]: {bad_total.unique()}"
    )

    yes_no_map = {0: "no", 1: "yes"}

    # prior cardiac procedures
    harmonized_df["has_had_percutaneous_coronary_intervention"] = map_with_check(
        harmonized_df["crf_pci"], yes_no_map
    )
    harmonized_df["has_had_coronary_artery_bypass_graft"] = map_with_check(
        harmonized_df["crf_cabg"], yes_no_map
    )

    # implanted cardiac devices
    harmonized_df["has_no_cardiac_device"] = map_with_check(
        harmonized_df["crf_devicenone"], yes_no_map
    )
    harmonized_df["has_pacemaker"] = map_with_check(harmonized_df["crf_pace"], yes_no_map)
    harmonized_df["has_biventricular_pacemaker"] = map_with_check(
        harmonized_df["crf_biv"], yes_no_map
    )
    harmonized_df["has_implantable_cardioverter_defibrillator"] = map_with_check(
        harmonized_df["crf_icd"], yes_no_map
    )
    harmonized_df["has_biventricular_icd"] = map_with_check(
        harmonized_df["crf_bivicd"], yes_no_map
    )

    # heart failure etiology
    # NOTE: crf_cad does NOT reproduce the paper's published "Ischemic cause"
    # counts in Table 2 (control 69/157, intervention 73/157) -- raw crf_cad
    # gives control 72/157, intervention 63/157, direction even reversed.
    # Flagging in case anyone downstream expects it to match the paper.
    harmonized_df["is_heart_failure_etiology_ischemic"] = map_with_check(
        harmonized_df["crf_cad"], yes_no_map
    )
    harmonized_df["is_heart_failure_etiology_hypertensive"] = map_with_check(
        harmonized_df["crf_ethtn"], yes_no_map
    )
    harmonized_df["is_heart_failure_etiology_valvular"] = map_with_check(
        harmonized_df["crf_etval"], yes_no_map
    )
    harmonized_df["is_heart_failure_etiology_alcohol_related"] = map_with_check(
        harmonized_df["crf_etalc"], yes_no_map
    )
    harmonized_df["is_heart_failure_etiology_idiopathic_or_other"] = map_with_check(
        harmonized_df["crf_etidi"], yes_no_map
    )

    # allergies, free text - left as-is, just renamed
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
        + tics_cols
    ]
