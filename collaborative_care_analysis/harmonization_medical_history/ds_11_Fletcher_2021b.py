import pandas as pd

from collaborative_care_analysis.utils import map_with_check


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    harmonized_df = df.copy()

    # Medical history&comorbidity data for this dataset is very limited
    # compared to other harmonized datasets (Hölzel, Bekelman, Aragones):
    # the raw export has no disease-specific fields (no diabetes/
    # hypertension/cancer/cardiovascular breakdown). Verified by:
    #   - searching the full codebook log for diabetes/hypertension/
    #     cardio/cancer/asthma/arthritis/stroke/copd/comorbid/chronic -
    #     the only hits were free-text example answers in unrelated
    #     open-ended fields (e.g. a one-off "Diabetes and medication" in
    #     an ER-visit reason field), not a coded comorbidity variable;
    #   - OCR-scanning 117 slides of the trial's own follow-up survey
    #     screenshots for the same terms, with no relevant hits.
    # The only usable field is "illness_t", a single generic "Long term
    # Illness" yes/no item (per the codebook), fully populated (0/1,868
    # missing).
    #
    # illness_t is a "toolkit" variable (column suffix "_t" in the raw
    # data). load()'s to_long() already attaches toolkit columns only to
    # the baseline (follow_up_months == 0) row and sets them to NaN at
    # all other follow-up rows - this is a structural feature of
    # load(), not a data-quality issue, so no extra baseline-only
    # handling is needed here (unlike ds_05_Bekelman_2015's CRF_*
    # fields, which required an explicit fix).
    #
    # Other candidate fields were deliberately excluded from this
    # cluster because they are not disease diagnoses:
    #   - health_0 / health_3grps_0 / health_2grps_0: self-rated general
    #     health (Excellent..Poor) - a subjective rating, not a
    #     diagnosis.
    #   - psychpast_0: number of psychologist/counsellor visits in the
    #     past 12 months - mental-health service utilization, not a
    #     diagnosis.
    #   - antidepressants_0: current antidepressant use - medication
    #     use, not a diagnosis.
    #   - antipsychotics_0: constant "No" for all 1,868 patients. In my opinion, this is
    #     not a data-quality issue: per the published trial paper
    #     (Fletcher et al. 2021, Br J Gen Pract), current antipsychotic
    #     use was a trial exclusion criterion, so this field has zero
    #     variance by design and carries no comorbidity information.
    #   - disability_1: receiving a disability benefit - a
    #     socioeconomic/functional-status field, not a diagnosis.
    #   - risk: the trial's own CPT ("diamond") depression-severity
    #     prognosis classification (minimal/mild, moderate, severe),
    #     confirmed by the published paper - not medical history.
    assert "illness_t" in harmonized_df.columns, "illness_t column missing from the export"

    yes_no_map = {0: "no", 1: "yes"}

    harmonized_df["has_long_term_illness"] = map_with_check(  # illness_t
        # PRESENCE: a single umbrella yes/no item ("Long term Illness"
        # per the codebook)-unlike Hölzel's CDI checklist or
        # ds_05_Bekelman_2015's CRF_* fields, this dataset does not let
        # us tell which condition(s), if any, a "yes" refers to.
        harmonized_df["illness_t"],
        yes_no_map,
        "illness_t",
    )

    # return the harmonized dataset which has only the values we want
    return harmonized_df[
        [
            "STUDY_ID",
            "patient_id",
            "follow_up_months",
            "has_long_term_illness",
        ]
    ]
