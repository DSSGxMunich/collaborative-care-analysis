import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()
    # Chronic Disease Index (CDI) items, per the German IMPACT / Hölzel et al.
    # 2018 codebook. Collected once, at baseline only (GI_B1_CDI_*) - these
    # columns are NaN at follow_up_months != 0 in the long-format frame.
    # Raw coding: 0 = Nein (no), 1 = Ja (yes), 9 = missing value sentinel.
    #
    # NOTE ON MEANING: we only have the short variable label for each item
    # (e.g. "CDI Knochenbruch"), not the actual question wording from the
    # patient-facing form. CDI-style comorbidity checklists are typically
    # "have you ever been diagnosed with / do you have this condition"
    # (i.e. presence/history, not "is it currently active right now"). - These variables are non-etiological because they indicate whether a condition is present or has a history, rather than why it occurred.
    cdi_cols = [f"CDI_{i}" for i in range(1, 19)]

    missing_cols = [c for c in cdi_cols if c not in harmonized_df.columns]
    assert not missing_cols, f"Expected CDI columns missing from the export: {missing_cols}"

    # 9 is a declared missing-value code, not "no". Neutralize it before
    # mapping so map_with_check doesn't need 9 in its dict and it stays NaN.
    harmonized_df[cdi_cols] = harmonized_df[cdi_cols].replace(9, pd.NA)

    yes_no_map = {0: "no", 1: "yes"}

    # cardiac conditions
    harmonized_df["has_angina"] = map_with_check(  # CDI_1: Angina
        # Chest pain from reduced blood flow to the heart - a symptom/
        # diagnosis of coronary artery disease, not a heart attack itself.
        harmonized_df["CDI_1"],
        yes_no_map,
        "CDI_1",
    )
    harmonized_df["has_heart_failure_diagnosis"] = map_with_check(  # CDI_2: Herzschwäche
        # Heart can't pump blood effectively enough for the body's needs
        # (a chronic condition, not a one-time event).
        harmonized_df["CDI_2"],
        yes_no_map,
        "CDI_2",
    )
    harmonized_df["has_history_of_heart_attack"] = map_with_check(  # CDI_3: Herzinfarkt
        # History of myocardial infarction - a past acute event, asking
        # "did this ever happen", not "is one happening now".
        harmonized_df["CDI_3"],
        yes_no_map,
        "CDI_3",
    )

    # respiratory
    harmonized_df["has_asthma_or_copd"] = map_with_check(  # CDI_4: Asthma/ Bronchitis/ Emphysem
        # Single combined item covering three distinct chronic lung
        # conditions (asthma, bronchitis, emphysema) - the source data does
        # not let us tell which of the three a "yes" refers to.
        harmonized_df["CDI_4"],
        yes_no_map,
        "CDI_4",
    )

    # musculoskeletal
    harmonized_df["has_arthritis"] = map_with_check(  # CDI_5: Arthritis
        # Joint inflammation/pain condition (rheumatoid or osteoarthritis -
        # the item doesn't distinguish which type).
        harmonized_df["CDI_5"],
        yes_no_map,
        "CDI_5",
    )
    harmonized_df["has_osteoporosis"] = map_with_check(  # CDI_6: Osteoporose
        # Bone-density loss / brittle-bone diagnosis.
        harmonized_df["CDI_6"],
        yes_no_map,
        "CDI_6",
    )
    harmonized_df["has_bone_fracture"] = map_with_check(  # CDI_7: Knochenbruch
        # History of (at least one) broken bone -- like has_history_of_heart_attack,
        # this is "did this ever happen", not an active/current fracture.
        harmonized_df["CDI_7"],
        yes_no_map,
        "CDI_7",
    )
    harmonized_df["has_joint_replacement"] = map_with_check(  # CDI_8: Gelenkersatz
        # Prosthetic joint surgery (e.g. hip/knee replacement) - a past
        # procedure, so "yes" means it happened at some point, not that
        # surgery is scheduled or ongoing.
        harmonized_df["CDI_8"],
        yes_no_map,
        "CDI_8",
    )
    harmonized_df["has_joint_fusion"] = map_with_check(  # CDI_9: Gelenkversteifung
        # Joint surgically or naturally fused/stiffened (ankylosis) -
        # distinct from joint_replacement above, no prosthesis involved.
        harmonized_df["CDI_9"],
        yes_no_map,
        "CDI_9",
    )
    harmonized_df["has_amputation"] = map_with_check(  # CDI_10: Amputation
        # Loss of a limb or part of one, by surgery or injury.
        harmonized_df["CDI_10"],
        yes_no_map,
        "CDI_10",
    )

    # neurological
    harmonized_df["has_parkinsons_disease"] = map_with_check(  # CDI_11: Parkinson
        # Progressive neurological disorder affecting movement.
        harmonized_df["CDI_11"],
        yes_no_map,
        "CDI_11",
    )
    harmonized_df["has_stroke"] = map_with_check(  # CDI_12: Schlaganfall
        # History of stroke (cerebrovascular event) -- again a past event,
        # not "currently having a stroke".
        harmonized_df["CDI_12"],
        yes_no_map,
        "CDI_12",
    )

    # other chronic conditions
    harmonized_df["has_sleep_disorder"] = map_with_check(  # CDI_13: Schlafstörungen
        # General sleep-disturbance item (insomnia, etc.) -- not specific
        # to a diagnosis like sleep apnea.
        harmonized_df["CDI_13"],
        yes_no_map,
        "CDI_13",
    )
    harmonized_df["has_chronic_pain_syndrome"] = (
        map_with_check(  # CDI_14: Chronisches Schmerzsyndrom
            # Ongoing/persistent pain condition, as opposed to acute short-term
            # pain (e.g. from a recent injury).
            harmonized_df["CDI_14"],
            yes_no_map,
            "CDI_14",
        )
    )
    harmonized_df["has_cancer"] = map_with_check(  # CDI_15: Krebs
        # History of a cancer diagnosis - item doesn't specify type,
        # stage, or whether currently in remission/treatment.
        harmonized_df["CDI_15"],
        yes_no_map,
        "CDI_15",
    )
    harmonized_df["has_diabetes"] = map_with_check(  # CDI_16: Diabetes
        # Diabetes diagnosis - item doesn't distinguish type 1 vs type 2.
        harmonized_df["CDI_16"],
        yes_no_map,
        "CDI_16",
    )

    # eye conditions
    harmonized_df["has_glaucoma"] = map_with_check(  # CDI_17: Glaukom
        # Eye condition involving optic-nerve damage, often from elevated
        # intraocular pressure; can lead to vision loss if untreated.
        harmonized_df["CDI_17"],
        yes_no_map,
        "CDI_17",
    )
    harmonized_df["has_cataract"] = map_with_check(  # CDI_18: Katarakt
        # Clouding of the eye's lens - common age-related condition.
        harmonized_df["CDI_18"],
        yes_no_map,
        "CDI_18",
    )

    # return the harmonized dataset which has only the values we want
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "study_arm",
            "follow_up_months",
            "has_angina",
            "has_heart_failure_diagnosis",
            "has_history_of_heart_attack",
            "has_asthma_or_copd",
            "has_arthritis",
            "has_osteoporosis",
            "has_bone_fracture",
            "has_joint_replacement",
            "has_joint_fusion",
            "has_amputation",
            "has_parkinsons_disease",
            "has_stroke",
            "has_sleep_disorder",
            "has_chronic_pain_syndrome",
            "has_cancer",
            "has_diabetes",
            "has_glaucoma",
            "has_cataract",
        ]
    ]
