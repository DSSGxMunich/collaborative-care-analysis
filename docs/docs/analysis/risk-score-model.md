# Risk score model (Step 1)

`collaborative_care_analysis/data_analysis/risk_score_model.R` fits a
**prognostic model for PHQ-9 at 12 months**. Its linear predictor, *eta*, is
the patient's **risk score**. The Step 2
[component network model](cnma.md) uses this score as an effect modifier.

## Model

A **cumulative-logit (proportional-odds) mixed model**, fitted with
`ordinal::clmm`. Each PHQ-9 value (0–27) is treated as an ordered category:

```text
logit P(Y ≤ j | X, u_s) = θ_j − (Xβ + u_0s + u_1s · y0_c)
```

| Term                  | Meaning                                                                |
|-----------------------|------------------------------------------------------------------------|
| `Y`                   | PHQ-9 total at 12 months (`phq9_total_outcome`)                         |
| `y0_c`                | Baseline PHQ-9, standardized                                           |
| `ns(age_c, …)`        | Natural cubic spline of standardized age. Boundary knots at the 5th/95th percentiles, interior knots at the 35th/65th |
| `sex`                 | Factor                                                                 |
| `u_0s`, `u_1s`        | Random intercept and random baseline-PHQ-9 slope per study (independent; estimating their correlation stops the solver converging) |

The **risk score** is `eta = Xβ` with the study effects set to zero. That
makes it usable for patients from studies that were not in the development
data.

## Fitting

```bash
Rscript collaborative_care_analysis/data_analysis/risk_score_model.R fit
```

This requires R with `data.table`, `ordinal` and `splines`. It reads:

```text
data/interim/analysis_datasets/phq9_12mo_core/wide.csv
```

The file needs the columns `STUDY_ID`, `patient_id`, `phq9_total_outcome`,
`phq9_total_baseline`, `age` and `sex`. Rows with any of these missing are
dropped.

!!! warning
    This input path and these column names differ from what
    `dataset_creation.create_wide()` currently writes
    (`analysis_dataset_wide.csv` with `baseline_phq9` / `phq9_12mo`). See
    [Known issues](../reference/known-issues.md).

The script:

1. computes the centering constants and spline knots,
2. fits the model and prints its summary,
3. checks convergence with the **relative gradient** (`max.grad / |logLik|`)
   and warns if it is above `1e-3`,
4. saves a **lightweight model object** to `models/risk_score_model.rds`,
5. prints predictions for three synthetic example patients.

### Saved model object

| Field                         | Content                                               |
|-------------------------------|-------------------------------------------------------|
| `thresholds`, `beta`          | Cut-points θ and fixed-effect coefficients β          |
| `fixed_form`, `age_knots`     | Design formula and spline knots                       |
| `scaling`                     | Means/SDs used to standardize `y0` and `age`          |
| `age_range`, `sex_levels`, `ylevels` | Development ranges and levels                  |
| `sigma0`, `sigma1`            | SDs of the study random intercept and slope           |
| `n_studies`, `n_dev`, `cohort`, `fitted_on`, `r_version` | Provenance                 |

The fitted `clmm` object is **not** saved, because it would contain the
development data.

## Prediction

```r
source("collaborative_care_analysis/data_analysis/risk_score_model.R")
model <- readRDS(OUT_MODEL)
eta   <- predict_phq9(model, newdata)   # newdata: y0, age, sex
```

`predict_phq9()`:

- **errors** if `y0`, `age` or `sex` are missing, if `sex` has a level not seen
  in development, or if the design matrix does not match the stored
  coefficients,
- **warns** if `y0` is outside 0–27 or `age` is outside the development range,
- uses the stored factor levels, so a single-sex batch still produces the
  correct design matrix.
