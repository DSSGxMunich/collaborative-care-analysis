import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Medical history / comorbidity fields, per the Aragones et al. 2019
    # codebook. These come from TIME_INDEPENDENT_COLS in load(), so they
    # are duplicated identically into every follow_up_months row for a
    # given patient by construction - no risk of a "yes" flipping to
    # "no" across visits here (unlike ds_05_Bekelman_2015) :D
    #
    # DATA QUALITY NOTE: the codebook describes these fields
    # as "(1/0)", but the raw CSV never contains an explicit "0" - every
    # row is either "1" or blank (a checkbox-style CRF: mark if present,
    # leave blank if absent). Verified against an independently-coded
    # copy of this same patient population (a separate .dta file using
    # explicit 0="No"/1="Yes" labels for Diabetes, Hypertension, Cardiac,
    # Respiratory, Cancer, and Group): merging on patient ID gives a
    # 328/328 (100%) match between "blank" in the raw CSV and "No" in
    # the labelled file, for all five comorbidity fields. Blank
    # confidently means "No", not "unknown/not assessed".
    comorbidity_cols = [
        "HYPERT",
        "DIABETES",
        "RESPIRATORY",
        "CARDIOVASCULAR",
        "CANCER",
    ]

    missing_cols = [c for c in comorbidity_cols if c not in harmonized_df.columns]
    assert not missing_cols, (
        f"Expected comorbidity columns missing from the export: {missing_cols}"
    )

    # Raw values are the string "1" (present) or NaN (blank/not marked).
    # Fill NaN with "0" - confirmed to mean "No", see the note above.
    filled_comorbidity_cols = harmonized_df[comorbidity_cols].fillna("0")

    yes_no_map = {"0": "no", "1": "yes"}

    # cardiac / cardiovascular
    harmonized_df["has_hypertension"] = map_with_check(  # HYPERT
        # Reuses the name used in ds_05_Bekelman_2015 - same concept
        # (hypertension diagnosis), no granularity mismatch.
        filled_comorbidity_cols["HYPERT"],
        yes_no_map,
        "HYPERT",
    )
    harmonized_df["has_cardiovascular_disease"] = map_with_check(  # CARDIOVASCULAR
        # NOTE: a broad/umbrella category (unspecified cardiovascular
        # condition) - not the same granularity as the specific cardiac
        # fields used in other datasets (e.g.
        # has_history_of_heart_attack, has_had_percutaneous_coronary_
        # intervention, is_heart_failure_etiology_ischemic). Kept as its
        # own column rather than conflated with any single one of those.
        filled_comorbidity_cols["CARDIOVASCULAR"],
        yes_no_map,
        "CARDIOVASCULAR",
    )

    # metabolic
    harmonized_df["has_diabetes"] = map_with_check(  # DIABETES
        # Reuses the name used in ds_13_Hölzel_2018 and
        # ds_05_Bekelman_2015 - same concept, no granularity mismatch.
        filled_comorbidity_cols["DIABETES"],
        yes_no_map,
        "DIABETES",
    )

    # respiratory
    harmonized_df["has_respiratory_disease"] = map_with_check(  # RESPIRATORY
        # NOTE: a broad/umbrella category (unspecified respiratory
        # condition) - not directly comparable to more specific fields
        # in other datasets, e.g. ds_13_Hölzel_2018's
        # "has_asthma_or_copd" or ds_05_Bekelman_2015's
        # "has_chronic_obstructive_pulmonary_disease". Kept as its own
        # column rather than merged with either.
        filled_comorbidity_cols["RESPIRATORY"],
        yes_no_map,
        "RESPIRATORY",
    )

    # oncology
    harmonized_df["has_cancer"] = map_with_check(  # CANCER
        # Reuses the name used in ds_13_Hölzel_2018 - same concept, no
        # granularity mismatch.
        filled_comorbidity_cols["CANCER"],
        yes_no_map,
        "CANCER",
    )

    # Number of chronic conditions - a count, not a yes/no flag. Per the
    # codebook, this is a clinician-assessed total and NOT necessarily
    # the sum of the five yes/no fields above (it may include conditions
    # not separately listed). Raw values arrive as strings (e.g. "1",
    # "2") due to the same blank-cell handling in load(); convert to a
    # proper nullable integer type. No equivalent column exists in any
    # other harmonized dataset so far.
    assert "CHR_CONDITIONS" in harmonized_df.columns, (
        "CHR_CONDITIONS column missing from the export"
    )
    chr_conditions = pd.to_numeric(harmonized_df["CHR_CONDITIONS"], errors="raise").astype("Int64")
    assert (chr_conditions.dropna() >= 0).all(), "CHR_CONDITIONS has negative values"
    harmonized_df["number_of_chronic_conditions"] = chr_conditions

    # return the harmonized dataset which has only the values we want
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_hypertension",
            "has_diabetes",
            "has_respiratory_disease",
            "has_cardiovascular_disease",
            "has_cancer",
            "number_of_chronic_conditions",
        ]
    ]
