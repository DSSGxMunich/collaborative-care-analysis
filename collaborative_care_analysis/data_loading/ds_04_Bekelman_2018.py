import pandas as pd

from collaborative_care_analysis.config import RAW_DATASETS_DIR


def load(
    file_path=RAW_DATASETS_DIR / "04_Bekelman_2018" / "CASAforIPD-MA (1).csv",
    verbose=False,
):
    df = pd.read_csv(
        filepath_or_buffer=file_path,
        # these columns have mixed types, pd suggests to specify a dtype
        dtype={251: "str", 253: "str", 300: "str"},
    )

    df.dropna(how="all", axis=0, inplace=True)
    df.dropna(how="all", axis=1, inplace=True)
    df.columns = df.columns.str.strip()

    # Remove all columns that are not explained in the codebook.
    codebook_dict = pd.read_excel(
        io=RAW_DATASETS_DIR / "04_Bekelman_2018" / "Codebook_Bekelman et al. (2018).xlsx",
        sheet_name=None,
    )
    for name in codebook_dict:
        codebook_dict[name].dropna(how="all", inplace=True)
    for name, worksheet in list(codebook_dict.items())[1:]:
        worksheet.columns = worksheet.columns.str.strip()
        worksheet["Variable"] = worksheet["Variable"].str.strip()

    column_source_dict = {}
    for col in df.columns:
        column_source_dict[col] = []
        for name, worksheet in list(codebook_dict.items())[1:]:
            if col in worksheet["Variable"].values:
                column_source_dict[col].append(name)

    empty_cols = [col for col in column_source_dict if not column_source_dict[col]]
    df.drop(labels=empty_cols, axis=1, inplace=True)

    # Keep rows with at least one relevant patient score available.
    patient_score_cols = [
        "phqtotal",
        "phqtotalv2",
        "gadtotal",
        "ticstot",
        "ticstotv2",
        "kccqos",
    ]
    has_patient_score = df[patient_score_cols].notna().any(axis=1)
    df = df.loc[has_patient_score]

    # Column classification
    RAW_ID_COLS = ["studyid", "timept"]
    RAW_OUTCOME_COLS = ["deathday", "outday"]

    RAW_TIME_INDEPENDENT_COLS = [
        # demographics
        "dem_age",
        "dem_smoke",
        "dem_ed",
        "dem_wrk",
        "dem_rel",
        "dem_inc",
        "ins_other",
        "ins_priv",
        "gender",
        "ethnic",
        "race",
        "raceotr",
        "age",
        # screening survey (baseline only)
        "scr_mdcare",
        "scr_mdcareotr",
        "scr_hfcare",
        "scr_hfcareotr",
        "scr_chfdx",
        "scr_hlth",
        "scr_tele",
        "scr_snf",
        "audit01",
        "audit02",
        "audit03",
        "subabuse",
        "scr_pain",
        "scr_ftg",
        "scr_sob",
        "scr_depr",
        "scr_crgvr",
        # case report form: medical history, labs, exam
        "crf_chf",
        "crf_allergies",
        "crf_mi",
        "crf_pci",
        "crf_cabg",
        "crf_dm",
        "crf_htn",
        "crf_pvd",
        "crf_cancer",
        "crf_tia",
        "crf_copd",
        "crf_afib",
        "crf_dvt",
        "crf_apnea",
        "crf_dep",
        "crf_ptsd",
        "crf_sa",
        "crf_sao",
        "crf_saospecify",
        "crf_devicenone",
        "crf_pace",
        "crf_biv",
        "crf_icd",
        "crf_bivicd",
        "crf_cad",
        "crf_ethtn",
        "crf_etval",
        "crf_etalc",
        "crf_etidi",
        "crf_ef",
        "crf_efclas",
        "crf_eftype",
        "crf_pulse",
        "crf_sys",
        "crf_dia",
        "crf_htin",
        "crf_wt",
        "crf_bmi",
        "crf_o2",
        "crf_edemarating",
        "crf_hg",
        "crf_bnptype",
        "crf_bnp",
        "crf_pbnp",
        "crf_bnpinout",
        "crf_albumin",
        "crf_tbil",
        "crf_ast",
        "crf_alt",
        "crf_chol",
        "crf_na",
        "crf_k",
        "crf_secr",
        "crf_egfr",
        "crf_fev1",
        "crf_fev1p",
        "crf_fvcp",
        "crf_pftratio",
        "crf_tsh",
        "crf_ecgdt",
        "crf_ecgqtint",
        "crf_ecgdur",
        "crf_ecgrate",
        "crf_ecgsinus",
        "crf_ecgpaced",
        "crf_ecgafib",
        "crf_ecglbbb",
        # service use
        "dem_card",
        "dem_pnspec",
        "dem_mh",
        "dem_pall",
        "dem_hspc",
        # trial design
        "site",
        "arm",
    ]

    RAW_TIME_DEPENDENT_COLS = [
        "tics01",
        "tics02",
        "tics03",
        "tics04",
        "tics05",
        "tics06",
        "tics07",
        "tics08",
        "tics09",
        "tics10",
        "tics11",
        "ticstot",
        "ticstotv2",
        "kccq01a",
        "kccq01b",
        "kccq01c",
        "kccq01d",
        "kccq01e",
        "kccq01f",
        "kccq02",
        "kccq03",
        "kccq04",
        "kccq05",
        "kccq06",
        "kccq07",
        "kccq08",
        "kccq09",
        "kccq10",
        "kccq11",
        "kccq12",
        "kccq13",
        "kccq14",
        "kccq15a",
        "kccq15b",
        "kccq15c",
        "kccq15d",
        "kccqpl",
        "kccqss",
        "kccqsf",
        "kccqsb",
        "kccqts",
        "kccqse",
        "kccqql",
        "kccqsl",
        "kccqcs",
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
        "facit01",
        "facit02",
        "facit03",
        "facit04",
        "facit05",
        "facit06",
        "facit07",
        "facit08",
        "facit09",
        "facit10",
        "facit11",
        "facit12",
        "facpeace",
        "facfaith",
        "factot",
        "eq5d01",
        "eq5d02",
        "eq5d03",
        "eq5d04",
        "eq5d05",
        "eq5d06",
        "eq5dtot",
        "msasck_pain",
        "msasck_energy",
        "msasck_cough",
        "msasck_drymouth",
        "msasck_nausea",
        "msasck_drowsy",
        "msasck_numbness",
        "msasck_sleep",
        "msasck_sob",
        "msasck_sexint",
        "msasck_const",
        "msasck_ot1",
        "msasck_ot2",
        "msas_pain",
        "msas_energy",
        "msas_cough",
        "msas_drymouth",
        "msas_nausea",
        "msas_drowsy",
        "msas_numbness",
        "msas_sleep",
        "msas_sob",
        "msas_sexint",
        "msas_constipation",
        "msas_ot1n",
        "msas_ot1",
        "msas_ot2n",
        "msas_ot2",
        "mut01",
        "mut02",
        "mut03",
        "mut04",
        "mut05",
        "mut06",
        "mut07",
        "mut09",
        "mut10",
        "mut11",
        "mut12",
        "mut13",
        "mut14",
        "mut15",
        "gsds01",
        "sx1",
        "sxotr1",
        "sx2",
        "sxotr2",
        "sx3",
        "sxotr3",
        "gsds02",
        "phq01",
        "phq02",
        "phq03",
        "phq04",
        "phq05",
        "phq06",
        "phq07",
        "phq08",
        "phq09",
        "phq10",
        "phqtotal",
        "phqtotalv2",
        "gad01",
        "gad02",
        "gad03",
        "gad04",
        "gad05",
        "gad06",
        "gad07",
        "gad08",
        "gadtotal",
        "peg01",
        "peg02",
        "peg03",
        "pegmean",
        "ftg01",
        "ftg02",
        "ftg03",
        "ftg04",
        "ftg05",
        "ftg06",
        "ftg07",
        "ftg08",
        "ftgtot",
        "dysp01",
        "dysp02",
        "dysp03",
        "dysptot",
        "dyspmean",
        "sds01",
        "sds02",
        "sds03",
        "sds04",
        "sds05",
        "schfi01",
        "schfi02",
        "schfi03",
        "schfi04",
        "schfi05",
        "schfi06",
        "schfi07",
        "schfi08",
        "schfi09",
        "schfi10",
        "schfi_11",
        "schfi11",
        "schfi12",
        "schfi13",
        "schfi14",
        "schfi15",
        "schfi16",
        "schfi17",
        "schfi18",
        "schfi19",
        "schfi20",
        "schfi21",
        "schfi22",
        "schfitot1",
        "schfitot2",
        "schfitot3",
        "nyha",
        "numervisits",
        "numhosp",
        "vstsrce___1",
        "vstsrce___2",
        "med_acein",
        "med_arb",
        "med_betab",
        "med_antid",
        "med_opi",
        "med_lpdiur",
        "med_aldrcnt",
        "med_dgxn",
        "med_statn",
        "satistot",
    ]

    RAW_CAREGIVER_COLS = [
        "cg_ptrel",
        "cg_live",
        "cg_yrs",
        "cg_hrs",
        "cg_yrslive",
        "cg_apt",
        "cg_yob",
        "cg_age",
        "cg_ed",
        "cg_work",
        "cg_wrkdscr",
        "cg_marstus",
        "cg_inc",
    ]

    TIMEPT_TO_MONTHS = {1: 0, 2: 3, 3: 6, 4: 12}

    # These columns should be renamed as per our convention.
    RENAME_MAP = {
        "studyid": "patient_id",
        "deathday": "days_until_death",
        "outday": "days_until_censoring",
    }

    # All patients should have some outcome (censoring or death) recorded.
    outcome_consistency = df.groupby("studyid")[RAW_OUTCOME_COLS].nunique()
    outcome_violations = outcome_consistency[(outcome_consistency > 1).any(axis=1)]
    if verbose:
        print(f"Patients with conflicting outcome values across visits: {len(outcome_violations)}")
        if len(outcome_violations):
            print(outcome_violations)
    assert len(outcome_violations) == 0, "Outcome columns disagree across a patient's rows"

    # Broadcast the single recorded value to every row for that patient.
    for col in RAW_OUTCOME_COLS:
        df[col] = df.groupby("studyid")[col].transform("max")

    if verbose:
        fully_missing = df.groupby("studyid")[RAW_OUTCOME_COLS].apply(
            lambda g: g.isna().all().all()
        )
        print(f"Patients with no outcome data at all: {fully_missing.sum()}")

    # Verify every column is accounted for.
    all_classified = (
        set(RAW_TIME_INDEPENDENT_COLS)
        | set(RAW_TIME_DEPENDENT_COLS)
        | set(RAW_CAREGIVER_COLS)
        | set(RAW_ID_COLS)
        | set(RAW_OUTCOME_COLS)
    )
    unaccounted = set(df.columns) - all_classified
    if verbose:
        print(f"Unaccounted columns: {unaccounted or 'none'}")

    buckets = RAW_TIME_INDEPENDENT_COLS + RAW_TIME_DEPENDENT_COLS + RAW_CAREGIVER_COLS
    duplicated = {c for c in buckets if buckets.count(c) > 1}
    if verbose:
        print(f"Duplicated across buckets: {duplicated or 'none'}")

    missing_from_data = all_classified - set(df.columns)
    if verbose:
        print(f"Classified but absent from data: {missing_from_data or 'none'}")

    assert not unaccounted, "Unclassified columns would be dropped"
    assert not duplicated, "Columns appear in multiple buckets"

    # Structural checks on the patient/visit level.
    assert df["studyid"].notna().all(), "Rows with missing studyid"
    assert df["timept"].notna().all(), "Rows with missing timept"

    dupes = df.duplicated(subset=["studyid", "timept"], keep=False)
    if verbose:
        print(f"\nDuplicate studyid/timept rows: {dupes.sum()}")
        if dupes.any():
            print(df.loc[dupes, ["studyid", "timept"]].sort_values(["studyid", "timept"]))
    assert not dupes.any(), "Duplicate patient-visit rows"

    if verbose:
        print(f"Patients: {df['studyid'].nunique()}, rows: {len(df)}")
        print(f"timept values: {sorted(df['timept'].unique())}")
        print(f"\nVisits per patient:\n{df.groupby('studyid').size().value_counts().sort_index()}")

    # A static column that actually varies would be silently flattened by any
    # downstream collapse-to-baseline.
    static_variation = df.groupby("studyid")[RAW_TIME_INDEPENDENT_COLS].nunique().max()
    violations = static_variation[static_variation > 1].sort_values(ascending=False)
    if verbose:
        print(f"Static columns that vary within a patient: {len(violations)}")
    assert len(violations) == 0, "Presumed static column is actually time-varying"

    # Normalize the time axis. follow_up_months is a NEW column, not a rename,
    # so it's introduced directly rather than routed through RENAME_MAP.
    df["follow_up_months"] = df["timept"].map(TIMEPT_TO_MONTHS)
    unmapped = df.loc[df["follow_up_months"].isna(), "timept"].unique()
    assert len(unmapped) == 0, f"Unmapped timept codes: {unmapped}"
    df.drop(labels="timept", axis=1, inplace=True)

    keep_cols_raw = (
        ["studyid", "follow_up_months"]
        + RAW_TIME_INDEPENDENT_COLS
        + RAW_TIME_DEPENDENT_COLS
        + RAW_OUTCOME_COLS
    )
    df = df[keep_cols_raw].sort_values(["studyid", "follow_up_months"]).reset_index(drop=True)

    df.rename(columns=RENAME_MAP, inplace=True, errors="raise")

    if verbose:
        print(f"\nHarmonized long frame: {df.shape}")
        print(f"  {len(RAW_TIME_INDEPENDENT_COLS)} static")
        print(f"  {len(RAW_TIME_DEPENDENT_COLS)} time-varying")
        print(f"  {len(RAW_OUTCOME_COLS)} outcome")
        print(f"  {len(RAW_CAREGIVER_COLS)} caregiver columns dropped")

    cols_first = [
        "patient_id",
        "follow_up_months",
        "arm",
        "days_until_censoring",
        "days_until_death",
    ]
    remaining = [c for c in df.columns if c not in cols_first]
    df = df[cols_first + remaining]
    return df
