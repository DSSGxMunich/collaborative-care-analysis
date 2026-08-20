import pandas as pd


def _map_with_check(series: pd.Series, mapping: dict, label: str) -> pd.Series:
    """Map a series through a dict, asserting no unmapped (non-null) values exist.

    .map() silently returns NA for any value not present in the mapping, which
    can hide bad/unexpected raw codes. This makes that failure loud instead.
    """
    unmapped = series.dropna()[~series.dropna().isin(mapping)]
    assert unmapped.empty, f"{label}: unmapped values present: {unmapped.unique()}"
    return series.map(mapping)


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # patient_id: renamed from raw "studyid" (which is actually the
    # per-patient id within this trial, not a study-level id).
    harmonized_df = harmonized_df.rename(columns={"studyid": "patient_id"})

    # follow_up_months: months since baseline (baseline = 0), per convention.
    # Raw "timept" also has a value for the pre-baseline screening visit
    # (0), which isn't a follow-up relative to baseline -- left as missing
    # rather than forced into the numeric scale.
    timept_map = {1: 0, 2: 3, 3: 6, 4: 12}
    harmonized_df["follow_up_months"] = _map_with_check(
        harmonized_df["timept"], timept_map, "timept"
    )

    # study arm, human-readable (same convention as the treatment-info cluster)
    study_arm_map = {1: "control", 2: "intervention"}
    harmonized_df["study_arm"] = _map_with_check(harmonized_df["arm"], study_arm_map, "arm")

    yes_no_map = {0: "no", 1: "yes"}

    # prior cardiac procedures
    harmonized_df["has_had_percutaneous_coronary_intervention"] = _map_with_check(
        harmonized_df["crf_pci"], yes_no_map, "crf_pci"
    )
    harmonized_df["has_had_coronary_artery_bypass_graft"] = _map_with_check(
        harmonized_df["crf_cabg"], yes_no_map, "crf_cabg"
    )

    # implanted cardiac devices
    harmonized_df["has_no_cardiac_device"] = _map_with_check(
        harmonized_df["crf_devicenone"], yes_no_map, "crf_devicenone"
    )
    harmonized_df["has_pacemaker"] = _map_with_check(
        harmonized_df["crf_pace"], yes_no_map, "crf_pace"
    )
    harmonized_df["has_biventricular_pacemaker"] = _map_with_check(
        harmonized_df["crf_biv"], yes_no_map, "crf_biv"
    )
    harmonized_df["has_implantable_cardioverter_defibrillator"] = _map_with_check(
        harmonized_df["crf_icd"], yes_no_map, "crf_icd"
    )
    harmonized_df["has_biventricular_icd"] = _map_with_check(
        harmonized_df["crf_bivicd"], yes_no_map, "crf_bivicd"
    )

    # heart failure etiology
    # NOTE: crf_cad does NOT reproduce the paper's published "Ischemic cause"
    # counts in Table 2 (control 69/157, intervention 73/157) -- raw crf_cad
    # gives control 72/157, intervention 63/157, direction even reversed.
    # Flagging in case anyone downstream expects it to match the paper.
    harmonized_df["is_heart_failure_etiology_ischemic"] = _map_with_check(
        harmonized_df["crf_cad"], yes_no_map, "crf_cad"
    )
    harmonized_df["is_heart_failure_etiology_hypertensive"] = _map_with_check(
        harmonized_df["crf_ethtn"], yes_no_map, "crf_ethtn"
    )
    harmonized_df["is_heart_failure_etiology_valvular"] = _map_with_check(
        harmonized_df["crf_etval"], yes_no_map, "crf_etval"
    )
    harmonized_df["is_heart_failure_etiology_alcohol_related"] = _map_with_check(
        harmonized_df["crf_etalc"], yes_no_map, "crf_etalc"
    )
    harmonized_df["is_heart_failure_etiology_idiopathic_or_other"] = _map_with_check(
        harmonized_df["crf_etidi"], yes_no_map, "crf_etidi"
    )

    # allergies, free text -- left as-is, just renamed
    harmonized_df = harmonized_df.rename(columns={"crf_allergies": "allergies_description"})

    # return the harmonized dataset which has only the values we want
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "study_arm",
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