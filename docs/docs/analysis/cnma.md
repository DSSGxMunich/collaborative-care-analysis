# Component network model (Step 2)

`notebooks/02_CNMA_version1.ipynb` implements **Step 2** of a PATH-style
analysis. It is a **component network meta-analysis (CNMA)** in which the
effect of each collaborative-care component can vary with the Step 1
[risk score](risk-score-model.md).

## Model

For patient *i* with risk score *R*ᵢ and component indicators *C*ᵢₖ:

```text
PHQ9_12m,i = α_study(i) + λ·R_i + Σ_k β_k·C_ik + Σ_k δ_k·C_ik·R_i + ε_i
```

| Term           | Meaning                                                  |
|----------------|----------------------------------------------------------|
| `α_study`      | Study-specific intercept                                 |
| `λ`            | Main effect of the prognostic score                      |
| `β_k`          | Main effect of component *k*                             |
| `δ_k`          | Component-by-risk interaction                            |

The model-implied effect of component *k* at risk score *R* is
**τₖ(R) = βₖ + δₖ·R**. The risk score is currently **not centered**, so R = 0
may not correspond to a typical patient. Always interpret βₖ together with
δₖ at observed values of R.

The model is Bayesian and is fitted with **PyMC**. The notebook summarizes
the posterior with **ArviZ**: HDIs, `r_hat`, ESS and MCSE.

## Inputs

| Input                                    | Source                                                    |
|------------------------------------------|-----------------------------------------------------------|
| Filtered longitudinal cohort             | `risk_score_dataset` module (see [Known issues](../reference/known-issues.md)) |
| Step 1 risk scores                       | `data/processed/risk_scores.csv` with `STUDY_ID`, `patient_id`, `risk_score` |
| Component indicators                     | `treatment_*` columns added by [enrichment](../pipeline/merge-and-enrich.md#enrichment) |

## Components

Components come from the enrichment sheet. Binary `yes` / `no` columns are
encoded as 1 / 0. `treatment_form_of_monitoring` is encoded as
`no → 0`, `in_person` / `by_phone → 1`. Control arms have all components
set to 0.

The current version (v1) uses **6 components** and the **7 studies** that
remain after all filters and have risk scores:

- `treatment_automated_follow_up_process_was_used`
- `treatment_counseling_was_provided_in_addition_to_medication_`
- `treatment_is_there_a_relapse_prevention_plan`
- `treatment_manual_based_psychotherapy`
- `treatment_patient_preference_was_considered_in_treatment_decisions`
- `treatment_were_family_and_friends_involved`

## Notebook steps

1. Load the filtered cohort and check it (Coventry 2015 keeps very few
   patients and is inspected explicitly).
2. Build one row per patient: baseline plus the PHQ-9 closest to 12 months
   within 11.5–12.5 months.
3. Left-merge the Step 1 risk scores and inspect unmatched patients before
   excluding them.
4. Attach and encode the components, and check them for missingness. Unmapped
   labels are never treated as 0.
5. Keep complete cases only.
6. Build the design matrices *X*_C and *X*_C ⊙ R.
7. **Rank diagnostics.** Check the rank of the patient-level component matrix,
   of the unique component packages and of the full predictor block, and list
   which study arms share a package. A rank below the number of components
   means some component effects cannot be separated.
8. Fit the Bayesian model and summarize the posterior. Good MCMC diagnostics
   do **not** fix a rank deficiency in the design.
9. Write the coefficients to `path_cnma_coefficients.csv`.

!!! warning "Notebook outputs"
    Notebook outputs are stripped before commit (see
    [Development](../development.md)). Even locally, keep any cell output
    that could show individual patients to aggregates only.
