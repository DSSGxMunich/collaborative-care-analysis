import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # -------------------------------------------------------------------
    # LONG-TERM ILLNESS
    # -------------------------------------------------------------------
    assert "illness_t" in harmonized_df.columns, "illness_t column missing from the export"
    yes_no_map = {0: "no", 1: "yes"}
    harmonized_df["has_long_term_illness"] = map_with_check(harmonized_df["illness_t"], yes_no_map)

    # -------------------------------------------------------------------
    # HEALTH / CONCESSION CARDS
    # -------------------------------------------------------------------
    # Three separate raw sources exist for card status, confirmed against
    # the .dta value labels (not guessed):
    #   1. "_0" (Screening survey): five separate yes/no flags.
    #   2. "_1" (Baseline survey, i.e. follow_up_months == 0 too, but a
    #      DIFFERENT survey administration per the Groups_Timeframe file:
    #      Screening=0, Baseline=1): the same five separate yes/no flags,
    #      asked again.
    #   3. "_2"/"_3" (3-month/12-month follow-up): a single consolidated
    #      categorical field ("card_2"/"card_3") where the patient picks
    #      one card type or "None" - confirmed via the .dta's own
    #      decoded categories, not previously available from the
    #      printed codebook log alone.
    # All three are kept as separate columns since they come from
    # different survey administrations and have different raw
    # structures; none are silently merged or assumed to describe the
    # same value at the same time.
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
        harmonized_df[new_col] = map_with_check(harmonized_df[raw_col], yes_no_map)

    # card_any_0: a combined "holds any card" summary flag, distinct
    # from the five individual card-type flags above.
    if "card_any_0" in harmonized_df.columns:
        harmonized_df["has_any_health_care_card"] = map_with_check(
            harmonized_df["card_any_0"], yes_no_map
        )
    else:
        harmonized_df["has_any_health_care_card"] = pd.NA

    # Baseline-survey ("_1") versions of the same five card-type flags.
    card_cols_1 = {
        "card_none_1": "has_no_health_care_card_baseline_survey",
        "card_vet_1": "has_veterans_affairs_card_baseline_survey",
        "card_sen_1": "has_commonwealth_seniors_health_card_baseline_survey",
        "card_pens_1": "has_pensioner_concession_card_baseline_survey",
        "card_health_1": "has_health_care_card_baseline_survey",
    }
    for raw_col, new_col in card_cols_1.items():
        if raw_col in harmonized_df.columns:
            harmonized_df[new_col] = map_with_check(harmonized_df[raw_col], yes_no_map)
        else:
            harmonized_df[new_col] = pd.NA

    # card_2/card_3: consolidated single-select card type at 3-month/
    # 12-month follow-up. Confirmed categories (from the .dta's own
    # decoded value labels): "Health Care Card (Centrelink)",
    # "Pensioner Concession Card (Centrelink)", "Commonwealth Seniors
    # Health Card", "Department of Veterans", "None". Kept as its own
    # column rather than forced into the five-flag structure above,
    # since a patient can only pick one value here.
    card_type_map = {
        0: "Health Care Card (Centrelink)",
        1: "Pensioner Concession Card (Centrelink)",
        2: "Commonwealth Seniors Health Card",
        3: "Department of Veterans",
        4: "None",
    }
    if "card" in harmonized_df.columns:
        harmonized_df["health_care_card_type_follow_up"] = map_with_check(
            harmonized_df["card"], card_type_map
        )
    else:
        harmonized_df["health_care_card_type_follow_up"] = pd.NA

    # -------------------------------------------------------------------
    # HEALTHCARE PROVIDER VISITS (per follow-up: "visits in the last
    # month" at each survey timepoint)
    # -------------------------------------------------------------------
    # NOTE FOR NOW: "domesticviolenceworkervisit" and "alcoholanddrugworkervisit"
    # are deliberately NOT included here - they are already used
    # in harmonization_baseline (as "domestic_violence_worker_visit" and
    # "alcohol_drug_worker_visit")
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
            harmonized_df[new_col] = map_with_check(harmonized_df[raw_stub], visits_map)
        else:
            harmonized_df[new_col] = pd.NA

    # family therapist: combine the two misspelled stub variants (see
    # note above) into a single column. combine_first() loses the
    # original Series' .name, so we restore one explicitly -- without
    # it, map_with_check would fall back to "<unnamed series>" in any
    # assertion error message.
    familytherapist_stubs = [
        c for c in ["familytherapistvisit", "familytherapisvisit"] if c in harmonized_df.columns
    ]
    assert familytherapist_stubs, (
        "Neither family-therapist visit column variant found in the export"
    )
    family_therapist_raw = harmonized_df[familytherapist_stubs[0]]
    for extra_stub in familytherapist_stubs[1:]:
        family_therapist_raw = family_therapist_raw.combine_first(harmonized_df[extra_stub])
    family_therapist_raw = family_therapist_raw.rename("/".join(familytherapist_stubs))
    harmonized_df["family_therapist_visit_frequency"] = map_with_check(
        family_therapist_raw, visits_map
    )

    # -------------------------------------------------------------------
    # "DID YOU VISIT AT ALL" GATEKEEPER FLAGS (only exist for these 4
    # providers, confirmed against the codebook - not present for the
    # others)
    # -------------------------------------------------------------------
    # These are separate raw fields from the *_visit frequency fields
    # above (e.g. "gp_visited_1" vs "gpvisit"). We don't have
    # documentation clarifying the exact relationship between the two
    # (e.g. whether "visited" is a skip-logic gate asked before the
    # frequency question, or an independent/redundant check) - included
    # as-is without assuming which.
    visited_gatekeeper_cols = {
        "gp_visited": "gp_visited_at_all",
        "counsellor_visited": "counsellor_visited_at_all",
        "psychiatrist_visited": "psychiatrist_visited_at_all",
        "psychol_visited": "psychologist_visited_at_all",
    }
    for raw_stub, new_col in visited_gatekeeper_cols.items():
        if raw_stub in harmonized_df.columns:
            harmonized_df[new_col] = map_with_check(harmonized_df[raw_stub], yes_no_map)
        else:
            harmonized_df[new_col] = pd.NA

    # -------------------------------------------------------------------
    # VISIT DETAILS: length, location, and out-of-pocket cost, for every
    # provider type already covered above (confirmed to exist in the
    # codebook for each of these; "domesticviolenceworker" has no such
    # detail fields, so it is not included)
    # -------------------------------------------------------------------
    length_map = {
        0: "Less than 6 mins",
        1: "7-19 mins",
        2: "20-39 mins",
        3: "40-60 mins",
        4: "More than 1 hour",
    }
    loc_map = {
        0: "Hospital",
        1: "GP clinic",
        2: "Community",
        3: "Outreach",
        4: "Private practice",
        5: "Other",
    }
    pay_map = {
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
    provider_detail_stubs = {
        "gp": "gp",
        "hospitaloutpatientdoctor": "hospital_outpatient_doctor",
        "specialistdoctor": "specialist_doctor",
        "physiotherapist": "physiotherapist",
        "chiropractor": "chiropractor",
        "psychologist": "psychologist",
        "counsellor": "counsellor",
        "psychiatrist": "psychiatrist",
        "nurse": "nurse",
        "socialworker": "social_worker",
        "complementarytherapist": "complementary_therapist",
        "supportgroup": "support_group",
        "pharmacist": "pharmacist",
        "othernaturaltherapist": "other_natural_therapist",
        # NOTE: "familytherapis" (no trailing "t") is the raw stub used
        # for these detail fields, matching the same misspelling pattern
        # seen for the visit-frequency field at follow-up timepoints.
        "familytherapis": "family_therapist",
        # "alcoholanddrugworker" visit FREQUENCY is already harmonized in
        # harmonization_baseline (as "alcohol_drug_worker_visit"); only
        # its length/location/payment DETAIL fields are added here,
        # since those are not covered anywhere else.
        "alcoholanddrugworker": "alcohol_drug_worker",
    }
    for raw_prefix, out_prefix in provider_detail_stubs.items():
        length_col = f"{raw_prefix}length"
        loc_col = f"{raw_prefix}loc"
        pay_col = f"{raw_prefix}pay"
        harmonized_df[f"{out_prefix}_visit_length"] = (
            map_with_check(harmonized_df[length_col], length_map)
            if length_col in harmonized_df.columns
            else pd.NA
        )
        harmonized_df[f"{out_prefix}_visit_location"] = (
            map_with_check(harmonized_df[loc_col], loc_map)
            if loc_col in harmonized_df.columns
            else pd.NA
        )
        harmonized_df[f"{out_prefix}_visit_out_of_pocket_cost"] = (
            map_with_check(harmonized_df[pay_col], pay_map)
            if pay_col in harmonized_df.columns
            else pd.NA
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
        25: "St John's Wort",
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
                harmonized_df[name_col], med_name_map
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

    # Antidepressant duration (baseline only). Confirmed against the
    # .dta's decoded categories: "adduration_0" carries the actual
    # duration bracket ("2 years or more", ..., "Don't know"). Its
    # companion field "AD_dur_0" is NOT included as a separate column:
    # checked directly, it has exactly the same non-missing count
    # (416/1868) as adduration_0 but only ever takes the value "Yes" -
    # i.e. it is a zero-variance skip-logic gate for the adduration_0
    # question, not a substantive answer on its own.
    ad_duration_map = {
        1: "1 month to less than 3 months",
        2: "3 months to less than 6 months",
        3: "6 months to less than 1 year",
        4: "1 year to less than 2 years",
        5: "2 years or more",
        6: "Don't know",
    }
    if "adduration_0" in harmonized_df.columns:
        harmonized_df["antidepressant_duration"] = map_with_check(
            harmonized_df["adduration_0"], ad_duration_map
        )
    else:
        harmonized_df["antidepressant_duration"] = pd.NA

    # -------------------------------------------------------------------
    # "DID THIS HAPPEN AT ALL" GATEKEEPER FLAGS for the ER/hospital/
    # medication sections below
    # -------------------------------------------------------------------
    any_flag_cols = {
        "anydiagnostictests": "had_any_diagnostic_tests",
        "anyervisits": "had_any_er_visits",
        "anymedicationtaken": "took_any_medication",
        "anyovernightstay": "had_any_overnight_stay",
    }
    for raw_stub, new_col in any_flag_cols.items():
        if raw_stub in harmonized_df.columns:
            harmonized_df[new_col] = map_with_check(harmonized_df[raw_stub], yes_no_map)
        else:
            harmonized_df[new_col] = pd.NA

    # -------------------------------------------------------------------
    # EMERGENCY DEPARTMENT VISITS (up to 4 ER episodes recorded per
    # survey)
    # -------------------------------------------------------------------
    er_type_map = {0: "private", 1: "public"}
    er_pay_map = pay_map
    for i in range(1, 5):
        reason_col = f"er_reason{i}"
        type_col = f"er_type{i}"
        pay_col = f"er_pay{i}"
        harmonized_df[f"er_visit_{i}_reason"] = (
            harmonized_df[reason_col] if reason_col in harmonized_df.columns else pd.NA
        )
        harmonized_df[f"er_visit_{i}_hospital_type"] = (
            map_with_check(harmonized_df[type_col], er_type_map)
            if type_col in harmonized_df.columns
            else pd.NA
        )
        harmonized_df[f"er_visit_{i}_out_of_pocket_cost"] = (
            map_with_check(harmonized_df[pay_col], er_pay_map)
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
            map_with_check(harmonized_df[type_col], stay_type_map)
            if type_col in harmonized_df.columns
            else pd.NA
        )
        harmonized_df[f"hospital_stay_{i}_nights"] = (
            map_with_check(harmonized_df[num_col], stay_num_map)
            if num_col in harmonized_df.columns
            else pd.NA
        )
        harmonized_df[f"hospital_stay_{i}_transport_method"] = (
            map_with_check(harmonized_df[transp_col], stay_transp_map)
            if transp_col in harmonized_df.columns
            else pd.NA
        )
        harmonized_df[f"hospital_stay_{i}_payment_source"] = (
            map_with_check(harmonized_df[pay_col], stay_pay_map)
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
        "has_any_health_care_card",
        *card_cols_1.values(),
        "health_care_card_type_follow_up",
        *provider_visit_cols.values(),
        "family_therapist_visit_frequency",
        *visited_gatekeeper_cols.values(),
    ]
    for out_prefix in provider_detail_stubs.values():
        output_cols += [
            f"{out_prefix}_visit_length",
            f"{out_prefix}_visit_location",
            f"{out_prefix}_visit_out_of_pocket_cost",
        ]
    for i in range(1, 6):
        output_cols += [
            f"medication_{i}_name",
            f"medication_{i}_dose",
            f"medication_{i}_duration",
        ]
    output_cols.append("antidepressant_duration")
    output_cols += list(any_flag_cols.values())
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
