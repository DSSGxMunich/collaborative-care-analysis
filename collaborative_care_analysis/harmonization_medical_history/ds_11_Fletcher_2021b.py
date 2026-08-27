import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # -------------------------------------------------------------------
    # LONG-TERM ILLNESS
    # -------------------------------------------------------------------
    assert "illness_t" in harmonized_df.columns, "illness_t column missing from the export"
    yes_no_map = {0: "no", 1: "yes"}
    harmonized_df["has_long_term_illness"] = map_with_check(
        harmonized_df["illness_t"], yes_no_map, "illness_t"
    )

    card_cols_0 = {
        "card_none_0": "has_no_health_care_card",
        "card_vet_0": "has_veterans_affairs_card",
        "card_sen_0": "has_commonwealth_seniors_health_card",
        "card_pens_0": "has_pensioner_concession_card",
        "card_health_0": "has_health_care_card",
    }
    missing_card_cols = [c for c in card_cols_0 if c not in harmonized_df.columns]
    assert not missing_card_cols, (
        f"Expected card columns missing from the export: {missing_card_cols}"
    )
    for raw_col, new_col in card_cols_0.items():
        harmonized_df[new_col] = map_with_check(harmonized_df[raw_col], yes_no_map, raw_col)

    # -------------------------------------------------------------------
    # HEALTHCARE PROVIDER VISITS (per follow-up: "visits in the last
    # month" at each survey timepoint)
    # -------------------------------------------------------------------
    # NOTE: "domesticviolenceworkervisit" and "alcoholanddrugworkervisit"
    # are deliberately NOT included here - they are already used
    # in harmonization_baseline (as "domestic_violence_worker_visit" and
    # "alcohol_drug_worker_visit").

    visits_map = {
        0: "0 times",
        1: "1-2 times",
        2: "3-4 times",
        3: "5-6 times",
        4: "7-11 times",
        5: "12 times or more",
    }
    provider_visit_cols = {
        "gpvisit": "gp_visit_frequency",
        "hospitaloutpatientdoctorvisit": "hospital_outpatient_doctor_visit_frequency",
        "specialistdoctorvisit": "specialist_doctor_visit_frequency",
        "physiotherapistvisit": "physiotherapist_visit_frequency",
        "chiropractorvisit": "chiropractor_visit_frequency",
        "psychologistvisit": "psychologist_visit_frequency",
        "counsellorvisit": "counsellor_visit_frequency",
        "psychiatristvisit": "psychiatrist_visit_frequency",
        "nursevisit": "nurse_visit_frequency",
        "socialworkervisit": "social_worker_visit_frequency",
        "complementarytherapistvisit": "complementary_therapist_visit_frequency",
        "supportgroupvisit": "support_group_visit_frequency",
        "pharmacistvisit": "pharmacist_visit_frequency",
        "othernaturaltherapistvisit": "other_natural_therapist_visit_frequency",
    }
    for raw_stub, new_col in provider_visit_cols.items():
        if raw_stub in harmonized_df.columns:
            harmonized_df[new_col] = map_with_check(harmonized_df[raw_stub], visits_map, raw_stub)
        else:
            harmonized_df[new_col] = pd.NA

    # family therapist: combine the two misspelled stub variants (see
    # note above) into a single column.
    familytherapist_stubs = [
        c for c in ["familytherapistvisit", "familytherapisvisit"] if c in harmonized_df.columns
    ]
    assert familytherapist_stubs, (
        "Neither family-therapist visit column variant found in the export"
    )
    family_therapist_raw = harmonized_df[familytherapist_stubs[0]]
    for extra_stub in familytherapist_stubs[1:]:
        family_therapist_raw = family_therapist_raw.combine_first(harmonized_df[extra_stub])
    harmonized_df["family_therapist_visit_frequency"] = map_with_check(
        family_therapist_raw, visits_map, "/".join(familytherapist_stubs)
    )

    # -------------------------------------------------------------------
    # MEDICATIONS (up to 5 medication slots recorded per survey)
    # -------------------------------------------------------------------
    med_name_map = {
        1: "Agomelatine / Valdoxan",
        2: "Amitriptyline / Endep",
        3: "Citalopram / Celapram / Celica / Ciazil / Cipramil / Citalobell / Talam / Talohexal",
        4: "Desvenlafaxine / Pristiq",
        5: "Dothiepin / Dothep / Prothiaden",
        6: "Duloxetine / Cymbalta / Drulox",
        7: "Escitalopram / Esipram / Esitalo / Lexam / Lexapro / Loxalate",
        8: "Fluoxetine / Auscap / Fluohexal / Fluoxebell / Levan / Prozac / Zactin",
        9: "Fluvoxamine / Faverin / Luvox / Movox / Voxam",
        10: "Mirtazapine / Avanza / Axit / Remeron",
        11: "Paroxetine / Aropax / Extine / Paxtine",
        12: "Sertraline / Concorz / Eleva / Sertra / Setrona / Xydep / Zoloft",
        13: "Venlafaxine / Efexor",
        14: "Alprazolam / Alprax / Anxit / Kalma / Xanax / Zamhexal",
        15: "Diazepam / Antenex / Ducene / Ranzepam / Valium / Valpam",
        16: "Oxazepam / Alepam / Murelax / Serapax",
        17: "Temazepam / Normison / Temaze / Temtabs",
        18: "Zopiclone / Imovane / Imrest",
        19: "Lithium carbonate / Lithicarb / Quilonum",
        20: "Olanzapine / Zyprexa",
        21: "Quetiapine / Seroquel",
        22: "Sodium valproate / Epilim",
        23: "Clonazepam / Paxam / Rivotril",
        24: "Pain relief",
        25: "St John's Wart",
        26: "Valerian",
        27: "Vitamins / Minerals",
        28: "Other",
    }
    for i in range(1, 6):
        name_col = f"medication{i}_name"
        dose_col = f"medication{i}_dose"
        long_col = f"medication{i}_long"
        if name_col in harmonized_df.columns:
            harmonized_df[f"medication_{i}_name"] = map_with_check(
                harmonized_df[name_col], med_name_map, name_col
            )
        else:
            harmonized_df[f"medication_{i}_name"] = pd.NA
        harmonized_df[f"medication_{i}_dose"] = (
            harmonized_df[dose_col] if dose_col in harmonized_df.columns else pd.NA
        )
        # NOTE: despite the raw name "_long", this is free-text duration
        # ("how long have you taken this", e.g. "10 years"), not a
        # yes/no "long-term" flag.
        harmonized_df[f"medication_{i}_duration"] = (
            harmonized_df[long_col] if long_col in harmonized_df.columns else pd.NA
        )

    # -------------------------------------------------------------------
    # EMERGENCY DEPARTMENT VISITS (up to 4 ER episodes recorded per
    # survey)
    # -------------------------------------------------------------------

    er_type_map = {0: "private", 1: "public"}
    er_pay_map = {
        0: "$0-9",
        1: "$10-19",
        2: "$20-29",
        3: "$30-39",
        4: "$40-49",
        5: "$50-59",
        6: "$60-69",
        7: "$70-79",
        8: "$80-89",
        9: "$90-99",
        10: "$100+",
    }
    for i in range(1, 5):
        reason_col = f"er_reason{i}"
        type_col = f"er_type{i}"
        pay_col = f"er_pay{i}"
        harmonized_df[f"er_visit_{i}_reason"] = (
            harmonized_df[reason_col] if reason_col in harmonized_df.columns else pd.NA
        )
        harmonized_df[f"er_visit_{i}_hospital_type"] = (
            map_with_check(harmonized_df[type_col], er_type_map, type_col)
            if type_col in harmonized_df.columns
            else pd.NA
        )
        harmonized_df[f"er_visit_{i}_out_of_pocket_cost"] = (
            map_with_check(harmonized_df[pay_col], er_pay_map, pay_col)
            if pay_col in harmonized_df.columns
            else pd.NA
        )

    # -------------------------------------------------------------------
    # HOSPITAL ADMISSIONS (up to 4 stays recorded per survey)
    # -------------------------------------------------------------------

    stay_type_map = {0: "private", 1: "public", 2: "other"}
    stay_num_map = {
        0: "1",
        1: "2",
        2: "3",
        3: "4",
        4: "5",
        5: "6",
        6: "7",
        7: "8",
        8: "9",
        9: "10+",
    }
    stay_transp_map = {
        0: "ambulance",
        1: "bus",
        2: "bicycle",
        3: "car",
        4: "taxi",
        5: "train",
        6: "tram",
        7: "walk",
    }
    stay_pay_map = {0: "medicare", 1: "private", 2: "out_of_pocket"}
    for i in range(1, 5):
        reason_col = f"stay_reason{i}"
        type_col = f"stay_type{i}"
        num_col = f"stay_num{i}"
        transp_col = f"stay_transp{i}"
        pay_col = f"stay_pay{i}"
        harmonized_df[f"hospital_stay_{i}_reason"] = (
            harmonized_df[reason_col] if reason_col in harmonized_df.columns else pd.NA
        )
        harmonized_df[f"hospital_stay_{i}_hospital_type"] = (
            map_with_check(harmonized_df[type_col], stay_type_map, type_col)
            if type_col in harmonized_df.columns
            else pd.NA
        )
        harmonized_df[f"hospital_stay_{i}_nights"] = (
            map_with_check(harmonized_df[num_col], stay_num_map, num_col)
            if num_col in harmonized_df.columns
            else pd.NA
        )
        harmonized_df[f"hospital_stay_{i}_transport_method"] = (
            map_with_check(harmonized_df[transp_col], stay_transp_map, transp_col)
            if transp_col in harmonized_df.columns
            else pd.NA
        )
        harmonized_df[f"hospital_stay_{i}_payment_source"] = (
            map_with_check(harmonized_df[pay_col], stay_pay_map, pay_col)
            if pay_col in harmonized_df.columns
            else pd.NA
        )

    # -------------------------------------------------------------------
    # RETURN HARMONIZED MEDICAL HISTORY VARIABLES
    # -------------------------------------------------------------------
    output_cols = [
        "STUDY_ID",
        "patient_id",
        "follow_up_months",
        "has_long_term_illness",
        *card_cols_0.values(),
        *provider_visit_cols.values(),
        "family_therapist_visit_frequency",
    ]
    for i in range(1, 6):
        output_cols += [
            f"medication_{i}_name",
            f"medication_{i}_dose",
            f"medication_{i}_duration",
        ]
    for i in range(1, 5):
        output_cols += [
            f"er_visit_{i}_reason",
            f"er_visit_{i}_hospital_type",
            f"er_visit_{i}_out_of_pocket_cost",
        ]
    for i in range(1, 5):
        output_cols += [
            f"hospital_stay_{i}_reason",
            f"hospital_stay_{i}_hospital_type",
            f"hospital_stay_{i}_nights",
            f"hospital_stay_{i}_transport_method",
            f"hospital_stay_{i}_payment_source",
        ]

    return harmonized_df[output_cols]
