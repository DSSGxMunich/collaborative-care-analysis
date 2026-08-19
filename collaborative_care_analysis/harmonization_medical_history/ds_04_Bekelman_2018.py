import pandas as pd


def harmonize_medical_history(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # study arm, human-readable (same convention as the treatment-info cluster)
    harmonized_df["study_arm"] = harmonized_df["arm"].map(
        {
            1: "control",
            2: "intervention",
        }
    )

    # prior cardiac procedures
    harmonized_df["percutaneous_coronary_intervention"] = harmonized_df["crf_pci"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["coronary_artery_bypass_graft"] = harmonized_df["crf_cabg"].map(
        {
            0: "no",
            1: "yes",
        }
    )

    # implanted cardiac devices
    harmonized_df["no_cardiac_device"] = harmonized_df["crf_devicenone"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["pacemaker"] = harmonized_df["crf_pace"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["biventricular_pacemaker"] = harmonized_df["crf_biv"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["implantable_cardioverter_defibrillator"] = harmonized_df["crf_icd"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["biventricular_icd"] = harmonized_df["crf_bivicd"].map(
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
    harmonized_df["heart_failure_etiology_ischemic"] = harmonized_df["crf_cad"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["heart_failure_etiology_hypertensive"] = harmonized_df["crf_ethtn"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["heart_failure_etiology_valvular"] = harmonized_df["crf_etval"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["heart_failure_etiology_alcohol"] = harmonized_df["crf_etalc"].map(
        {
            0: "no",
            1: "yes",
        }
    )
    harmonized_df["heart_failure_etiology_idiopathic_other"] = harmonized_df["crf_etidi"].map(
        {
            0: "no",
            1: "yes",
        }
    )

    # allergies, free text -- left as-is, just renamed
    harmonized_df["allergies"] = harmonized_df["crf_allergies"]

    # patient_id: renamed from raw "studyid" (which is actually the per-patient
    # id within this trial, not a study-level id). This resolves the reviewer
    # comment on PR #20 flagging "STUDY_ID" + "studyid" together as confusing --
    # keeping STUDY_ID (which study/dataset this row is from) and renaming the
    # raw patient identifier to something unambiguous.
    harmonized_df["patient_id"] = harmonized_df["studyid"]

    # return the harmonized dataset which has only the values I want
    # NOTE: ROW_ID must be kept -- dataset.py's harmonize pipeline raises a
    # ValueError if a harmonization function drops it (see traceback from
    # running `uv run collaborative_care_analysis/dataset.py harmonize`).
    
    return harmonized_df[
        [
            "STUDY_ID",
            "ROW_ID",
            "patient_id",
            "study_arm",
            "percutaneous_coronary_intervention",
            "coronary_artery_bypass_graft",
            "no_cardiac_device",
            "pacemaker",
            "biventricular_pacemaker",
            "implantable_cardioverter_defibrillator",
            "biventricular_icd",
            "heart_failure_etiology_ischemic",
            "heart_failure_etiology_hypertensive",
            "heart_failure_etiology_valvular",
            "heart_failure_etiology_alcohol",
            "heart_failure_etiology_idiopathic_other",
            "allergies",
        ]
    ]


# For development: Load data and run this harmonization function
if __name__ == "__main__":
    # Get the correct load() function (note the dataset id in the import path)
    from collaborative_care_analysis.data_loading.ds_04_Bekelman_2018 import load

    df = load()
    harmonized_df = harmonize_medical_history(df)
    print(harmonized_df.head())
