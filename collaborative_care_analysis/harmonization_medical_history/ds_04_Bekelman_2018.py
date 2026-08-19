import pandas as pd


def harmonize_medical_history(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # STUDY_ID: identifies which source study/dataset this row is from.
    # dataset.py no longer injects this automatically, so it's set explicitly
    # here.
    harmonized_df["STUDY_ID"] = "Bekelman_2018"

    # patient_id: renamed from raw "studyid" (which is actually the
    # per-patient id within this trial, not a study-level id).
    harmonized_df["patient_id"] = harmonized_df["studyid"]

    # follow_up_months: months since baseline (baseline = 0), per convention.
    # Raw "timept" also has a value for the pre-baseline screening visit
    # (0), which isn't a follow-up relative to baseline -- left as missing
    # rather than forced into the numeric scale.
    harmonized_df["follow_up_months"] = harmonized_df["timept"].map(
        {
            1: 0,  # baseline
            2: 3,
            3: 6,
            4: 12,
        }
    )

    # study arm, human-readable (same convention as the treatment-info cluster)
    harmonized_df["study_arm"] = harmonized_df["arm"].map(
        {
            1: "control",
            2: "intervention",
        }
    )

    # prior cardiac procedures
    harmonized_df["has_had_percutaneous_coronary_intervention"] = harmonized_df["crf_pci"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["has_had_coronary_artery_bypass_graft"] = harmonized_df["crf_cabg"].map(
        {
            0: "no",
            1: "yes",
        }
    )

    # implanted cardiac devices
    harmonized_df["has_no_cardiac_device"] = harmonized_df["crf_devicenone"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["has_pacemaker"] = harmonized_df["crf_pace"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["has_biventricular_pacemaker"] = harmonized_df["crf_biv"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["has_implantable_cardioverter_defibrillator"] = harmonized_df["crf_icd"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["has_biventricular_icd"] = harmonized_df["crf_bivicd"].map(
        {
            0: "no",
            1: "yes",
        }
    )

    # heart failure etiology
    # NOTE: crf_cad does NOT reproduce the paper's published "Ischemic cause"
    # counts in Table 2 (control 69/157, intervention 73/157) -- raw crf_cad
    # gives control 72/157, intervention 63/157, direction even reversed.
    # Flagging in case anyone downstream expects it to match the paper.
    harmonized_df["is_heart_failure_etiology_ischemic"] = harmonized_df["crf_cad"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["is_heart_failure_etiology_hypertensive"] = harmonized_df["crf_ethtn"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["is_heart_failure_etiology_valvular"] = harmonized_df["crf_etval"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["is_heart_failure_etiology_alcohol_related"] = harmonized_df["crf_etalc"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["is_heart_failure_etiology_idiopathic_or_other"] = harmonized_df[
        "crf_etidi"
    ].map(
        {
            0: "no",
            1: "yes",
        }
    )

    # allergies, free text -- left as-is, just renamed
    harmonized_df["allergies_description"] = harmonized_df["crf_allergies"]

    # return the harmonized dataset which has only the values I want
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


# For development: Load data and run this harmonization function
if __name__ == "__main__":
    # Get the correct load() function (note the dataset id in the import path)
    from collaborative_care_analysis.data_loading.ds_04_Bekelman_2018 import load

    df = load()
    harmonized_df = harmonize_medical_history(df)
    print(harmonized_df.head())
