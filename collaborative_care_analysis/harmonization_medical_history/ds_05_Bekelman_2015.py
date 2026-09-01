import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    # I created a copy so that we don't modify the original dataframe
    harmonized_df = df.copy()

    # -------------------------------------------------------------------------
    # STUDY ARM
    # -------------------------------------------------------------------------
    # Standardize the raw ARM values into the common study_arm categories
    # used across the harmonized datasets.
    harmonized_df["study_arm"] = map_with_check(
        harmonized_df["ARM"],
        {
            "Usual Care": "control",
            "Intervention": "intervention",
        },
        "ARM",
    )

    # -------------------------------------------------------------------------
    # MEDICAL HISTORY / COMORBIDITIES
    # -------------------------------------------------------------------------
    # Case-report-form (CRF_*) fields from the Schillok PCDM data
    # dictionary. Raw coding is uniformly 0 = No, 1 = Yes.
    #
    # NOTE: the PCDM data dictionary also lists CRF_CAD, CRF_ETHTN,
    # CRF_ETVAL, and CRF_ETIDI (heart failure etiology fields other than
    # alcohol-related). Checked directly against the raw CSV columns -
    # none of those four exist in the actual export (long or wide). Only
    # CRF_ETALC (alcohol-related etiology) is present, so that's the only
    # etiology field harmonized below. This dataset therefore can't
    # populate is_heart_failure_etiology_ischemic/hypertensive/valvular/
    # idiopathic_or_other the way ds_04_Bekelman_2018 does.
    crf_cols = [
        "CRF_MI",
        "CRF_PCI",
        "CRF_CABG",
        "CRF_ICD",
        "CRF_BIV",
        "CRF_PACE",
        "CRF_DM",
        "CRF_HTN",
        "CRF_TIA",
        "CRF_COPD",
        "CRF_AFIB",
        "CRF_PVD",
        "CRF_DEP",
        "CRF_PTSD",
        "CRF_APNEA",
        "CRF_SA",
        "CRF_SAO",
        "CRF_ETALC",
    ]

    missing_cols = [c for c in crf_cols if c not in harmonized_df.columns]
    assert not missing_cols, f"Expected CRF columns missing from the export: {missing_cols}"

    # DATA QUALITY ISSUE: these CRF_* fields are recorded at every survey
    # (baseline, 3-month, 6-month, final), not just at baseline - and
    # they are NOT stable over time the way a true medical history should
    # be. Checked directly against the raw long-format data for every
    # column above: in each one, the "yes -> no" flip count from baseline
    # to the last available follow-up massively outnumbers "no -> yes"
    # (e.g. CRF_MI: 145 yes->no vs 1 no->yes; CRF_HTN: 293 vs 3; CRF_TIA:
    # 29 vs 1; CRF_SA: 59 vs 0; even implant fields like CRF_ICD: 74 vs 2,
    # CRF_BIV: 19 vs 1, CRF_PACE: 43 vs 2). A prior heart attack, TIA,
    # hypertension diagnosis, or substance-abuse history cannot un-happen,
    # and a "yes" flipping to "no" this consistently across every single
    # field is not plausible as real clinical change -- it's a
    # data-quality artifact common to the whole CRF_* block (most likely
    # the follow-up CRF re-asks something different, e.g. "new event
    # since last visit", rather than re-confirming lifetime history /
    # current status).
    #
    # This reading is also consistent with the published trial protocol
    # (Bekelman et al. 2013, BMC Cardiovascular Disorders, Table 1):
    # medical history is not listed among the study's repeated-measures
    # outcomes (KCCQ, PHQ-9, SCL-20, medication adherence,
    # guideline-based care), which are the only measures explicitly
    # tracked at baseline/3-month/6-month/12-month. This supports medical
    # history being a baseline-only chart-review item rather than
    # something genuinely reassessed at every follow-up - though the
    # protocol does not spell out what, if anything, the follow-up CRF
    # was actually asking, so this remains our best interpretation rather
    # than a confirmed fact.
    #
    # CRF_DM is a partial exception: alongside the same yes->no artifact
    # (180 yes->no vs 10 no->yes), it has proportionally more no->yes
    # flips than other fields, plausibly reflecting some genuine new
    # diabetes diagnoses during the 12-month study. We still apply the
    # same baseline-only rule here for consistency with the rest of the
    # block, at the cost of potentially missing a handful of real
    # incident diabetes cases.
    #
    # I therefore only trust the baseline value for all of these columns
    # and blank out the follow-up rows.
    is_baseline = harmonized_df["follow_up_months"] == 0
    harmonized_df.loc[~is_baseline, crf_cols] = pd.NA

    yes_no_map = {0: "no", 1: "yes"}

    # cardiac history / procedures
    harmonized_df["has_history_of_heart_attack"] = map_with_check(  # CRF_MI: Prior MI
        # HISTORY: did the patient ever have a myocardial infarction --
        # a past event, not "is one happening right now".
        harmonized_df["CRF_MI"],
        yes_no_map,
        "CRF_MI",
    )
    harmonized_df["has_had_percutaneous_coronary_intervention"] = map_with_check(  # CRF_PCI
        # HISTORY: a past procedure (e.g. angioplasty/stent) to open a
        # blocked coronary artery -- "yes" means it happened at some
        # point, not that one is scheduled or ongoing.
        harmonized_df["CRF_PCI"],
        yes_no_map,
        "CRF_PCI",
    )
    harmonized_df["has_had_coronary_artery_bypass_graft"] = map_with_check(  # CRF_CABG
        # HISTORY: a past open-heart surgery rerouting blood flow around
        # a blocked coronary artery.
        harmonized_df["CRF_CABG"],
        yes_no_map,
        "CRF_CABG",
    )
    harmonized_df["has_implantable_cardioverter_defibrillator"] = map_with_check(  # CRF_ICD
        # CURRENT STATE: whether the patient has this device implanted
        # right now, not whether they ever had one (it could have been
        # removed).
        harmonized_df["CRF_ICD"],
        yes_no_map,
        "CRF_ICD",
    )
    harmonized_df["has_biventricular_pacemaker"] = map_with_check(  # CRF_BIV
        # CURRENT STATE: whether this specific device is currently
        # implanted.
        harmonized_df["CRF_BIV"],
        yes_no_map,
        "CRF_BIV",
    )
    harmonized_df["has_pacemaker"] = map_with_check(  # CRF_PACE
        # CURRENT STATE: a standard (non-biventricular) pacemaker
        # currently implanted.
        harmonized_df["CRF_PACE"],
        yes_no_map,
        "CRF_PACE",
    )
    harmonized_df["has_atrial_fibrillation_or_flutter"] = map_with_check(  # CRF_AFIB
        # DIAGNOSIS/PRESENCE: has this arrhythmia been diagnosed -
        # the item doesn't tell us if it's currently active/paroxysmal
        # vs. a past, resolved episode.
        harmonized_df["CRF_AFIB"],
        yes_no_map,
        "CRF_AFIB",
    )
    harmonized_df["has_peripheral_vascular_disease"] = map_with_check(  # CRF_PVD
        # DIAGNOSIS/PRESENCE: a diagnosed circulatory condition
        # (narrowed vessels outside the heart/brain), not an acute event.
        harmonized_df["CRF_PVD"],
        yes_no_map,
        "CRF_PVD",
    )

    # metabolic / respiratory
    harmonized_df["has_diabetes"] = map_with_check(  # CRF_DM
        # DIAGNOSIS/PRESENCE: item doesn't distinguish type 1 vs type 2.
        harmonized_df["CRF_DM"],
        yes_no_map,
        "CRF_DM",
    )
    harmonized_df["has_hypertension"] = map_with_check(  # CRF_HTN
        # DIAGNOSIS/PRESENCE: a chronic diagnosis, not a single elevated
        # reading.
        harmonized_df["CRF_HTN"],
        yes_no_map,
        "CRF_HTN",
    )
    harmonized_df["has_chronic_obstructive_pulmonary_disease"] = map_with_check(  # CRF_COPD
        # DIAGNOSIS/PRESENCE: a chronic lung-disease diagnosis.
        # NOTE: unlike Hölzel's combined "has_asthma_or_copd", this source
        # item is COPD only - don't collapse the two across datasets.
        harmonized_df["CRF_COPD"],
        yes_no_map,
        "CRF_COPD",
    )
    harmonized_df["has_sleep_apnea"] = map_with_check(  # CRF_APNEA
        # DIAGNOSIS/PRESENCE: a diagnosed sleep-breathing disorder
        # (repeated pauses/interruptions in breathing during sleep).
        # Per the published trial paper (Bekelman et al. 2015, Table 1),
        # this field specifically refers to OBSTRUCTIVE sleep apnea.
        #
        # NOT the same concept as Hölzel/ds_13's "has_sleep_disorder"
        # (source item: CDI_13, "Schlafstörungen" - German for general
        # sleep disturbances/insomnia). Sleep apnea is one specific
        # diagnosis; "sleep disorder" is an umbrella term that can cover
        # apnea, insomnia, restless legs syndrome, and other conditions,
        # without specifying which one. The two are not interchangeable:
        #   - A patient with "has_sleep_disorder = yes" (Hölzel) may or
        #     may not have apnea specifically - the source item doesn't
        #     say.
        #   - A patient with "has_sleep_apnea = no" (this dataset) could
        #     still have a different, undocumented sleep disorder.
        # Collapsing them into one shared column would either erase the
        # specific diagnosis this dataset actually captured, or would
        # incorrectly attribute a specific diagnosis (apnea) to patients
        # in Hölzel whose only recorded information is a general,
        # unspecified sleep complaint. They are therefore kept as two
        # separate, non-interchangeable columns across datasets.
        harmonized_df["CRF_APNEA"],
        yes_no_map,
        "CRF_APNEA",
    )

    # neurological
    harmonized_df["has_history_of_stroke_or_transient_ischemic_attack"] = (
        map_with_check(  # CRF_TIA
            # HISTORY: did the patient ever have a stroke or TIA - a past
            # event, not an active/ongoing one. Single combined item; the
            # source data doesn't let us tell stroke from TIA.
            harmonized_df["CRF_TIA"],
            yes_no_map,
            "CRF_TIA",
        )
    )

    # mental health / substance use
    harmonized_df["has_history_of_depression"] = map_with_check(  # CRF_DEP
        # HISTORY: a past/ever diagnosis, distinct from this dataset's
        # own baseline depression screen (see "was_depressed_at_baseline"
        # in the treatment harmonization module, derived from the
        # separate "depressed" field) - this CRF field is about
        # pre-existing history, not current screening status.
        harmonized_df["CRF_DEP"],
        yes_no_map,
        "CRF_DEP",
    )
    harmonized_df["has_history_of_post_traumatic_stress_disorder"] = map_with_check(  # CRF_PTSD
        # HISTORY: a past/ever diagnosis of PTSD.
        harmonized_df["CRF_PTSD"],
        yes_no_map,
        "CRF_PTSD",
    )
    harmonized_df["has_history_of_alcohol_abuse"] = map_with_check(  # CRF_SA
        # HISTORY: a past/ever diagnosis or documented history of alcohol
        # abuse, not current drinking status.
        harmonized_df["CRF_SA"],
        yes_no_map,
        "CRF_SA",
    )
    harmonized_df["has_history_of_other_substance_abuse"] = map_with_check(  # CRF_SAO
        # HISTORY: substance abuse other than alcohol; item doesn't
        # specify which substance(s).
        harmonized_df["CRF_SAO"],
        yes_no_map,
        "CRF_SAO",
    )

    # heart failure etiology (kept consistent with ds_04_Bekelman_2018's
    # is_heart_failure_etiology_* naming). Only the alcohol-related field
    # exists in this dataset's export - see the note above crf_cols.
    harmonized_df["is_heart_failure_etiology_alcohol_related"] = map_with_check(  # CRF_ETALC
        # ETIOLOGY: alcohol-related cardiomyopathy recorded as the
        # underlying cause of HF.
        harmonized_df["CRF_ETALC"],
        yes_no_map,
        "CRF_ETALC",
    )

    # -------------------------------------------------------------------------
    # RETURN HARMONIZED MEDICAL HISTORY VARIABLES
    # -------------------------------------------------------------------------
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_history_of_heart_attack",
            "has_had_percutaneous_coronary_intervention",
            "has_had_coronary_artery_bypass_graft",
            "has_implantable_cardioverter_defibrillator",
            "has_biventricular_pacemaker",
            "has_pacemaker",
            "has_atrial_fibrillation_or_flutter",
            "has_peripheral_vascular_disease",
            "has_diabetes",
            "has_hypertension",
            "has_chronic_obstructive_pulmonary_disease",
            "has_sleep_apnea",
            "has_history_of_stroke_or_transient_ischemic_attack",
            "has_history_of_depression",
            "has_history_of_post_traumatic_stress_disorder",
            "is_heart_failure_etiology_alcohol_related",
        ]
    ]
