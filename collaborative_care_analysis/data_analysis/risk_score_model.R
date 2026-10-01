# PHQ-9 at 12 months: proportional-odds mixed model
#
#   fit    :  Rscript collaborative_care_analysis/data_analysis/risk_score_model.R fit
#   predict:  source(".../risk_score_model.R"); predict_phq9(readRDS(OUT_MODEL), newdata)
#
# This file is the single definition of the risk model. The report in
# reports/risk-model.qmd sources it and uses the same data
# preparation, knots and formulas, so the documented model and the exported one
# cannot drift apart.
#
# newdata needs y0 (baseline PHQ-9), age (years) and sex.
#
# predict_phq9 type = "link" returns eta, the linear predictor, for a downstream
# model on the same cumulative-logit scale. type = "mean" returns E[Y | X], the
# conditional mean PHQ-9 at 12 months, for a downstream model on the score
# scale. The two are rank-identical but not linearly related, so an interaction
# fitted on one is not the same model as one fitted on the other.

library(splines)

script_path <- function() {
  # source() sets ofile; check it first, or sourcing this from another Rscript
  # would pick up that script's --file= instead of this one
  for (i in seq_len(sys.nframe())) {
    ofile <- sys.frame(i)$ofile
    if (!is.null(ofile)) return(normalizePath(ofile, mustWork = FALSE))
  }
  from_rscript <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  if (length(from_rscript))
    return(normalizePath(sub("^--file=", "", from_rscript[1]), mustWork = FALSE))
  NA_character_
}

repo_root <- function() {
  path <- script_path()
  if (!is.na(path) && nzchar(path))
    return(normalizePath(file.path(dirname(path), "..", ".."), mustWork = FALSE))
  dir <- normalizePath(getwd(), mustWork = FALSE)
  repeat {
    if (file.exists(file.path(dir, "pyproject.toml"))) return(dir)
    if (identical(dirname(dir), dir)) stop("cannot find the repository root")
    dir <- dirname(dir)
  }
}

REPO_ROOT <- repo_root()
DATA_PATH <- file.path(REPO_ROOT, "data", "processed", "analysis_datasets", "phq9_12mo_core", "wide.csv")
OUT_MODEL <- file.path(REPO_ROOT, "models", "risk_score_model.rds")

# Age spline knot percentiles. Cohort selection is not done here: which
# patients belong in the cohort is decided once, in dataset_creation.py, and
# recorded in spec.json next to the data.
AGE_KNOT_QUANTILES <- c(0.1, 0.5, 0.9)


# ----------------------------- Development data -----------------------------
load_model_data <- function(data_path = DATA_PATH) {
  # The analysis cohort, built by
  #   uv run collaborative_care_analysis/dataset.py analysis-data phq9_12mo_core
  library(data.table)

  if (!file.exists(data_path))
    stop("no development data at ", data_path,
         "\nbuild it with: uv run collaborative_care_analysis/dataset.py ",
         "analysis-data ", basename(dirname(data_path)))

  raw <- fread(data_path, na.strings = c("", "NA"))

  df <- raw[, .(study_id = factor(STUDY_ID),
                patient_id,
                phq9_at_12mo     = phq9_total_outcome,
                phq9_at_baseline = phq9_total_baseline,
                age,
                sex = factor(sex),
                arm = factor(study_arm))]

  # The cohort is already complete by construction; anything missing here means
  # the file was not built by the current spec.
  incomplete <- !complete.cases(df[, .(phq9_at_12mo, phq9_at_baseline, age, sex, arm)])
  if (any(incomplete))
    stop(sum(incomplete), " row(s) in ", basename(data_path),
         " have a missing predictor or outcome; rebuild the cohort with: ",
         "uv run collaborative_care_analysis/dataset.py analysis-data ",
         basename(dirname(data_path)))

  droplevels(df)
}


# --------------------------- Model specification ----------------------------
add_centred_terms <- function(df) {
  # Centre and scale on the development sample; the constants travel with the
  # fitted model so predictions use the same ones.
  scaling <- list(
    y0_mu  = mean(df$phq9_at_baseline), y0_sd  = sd(df$phq9_at_baseline),
    age_mu = mean(df$age),              age_sd = sd(df$age))

  df <- data.table::copy(df)
  df[, phq9_at_baseline_c := (phq9_at_baseline - scaling$y0_mu) / scaling$y0_sd]
  df[, age_c := (age - scaling$age_mu) / scaling$age_sd]

  list(data = df, scaling = scaling)
}

age_spline_knots <- function(df) {
  # Outer two are the boundary knots, the middle one is interior.
  as.numeric(quantile(df$age_c, AGE_KNOT_QUANTILES))
}

model_formulas <- function(knots) {
  # The knots live in the formulas' own environment rather than being inlined,
  # which keeps the fitted coefficient names readable. That environment travels
  # with the formula, so predict_phq9 can evaluate it on a fresh data frame
  # without the caller supplying anything.
  env <- new.env(parent = globalenv())
  env$age_knots <- knots

  spline_term <- quote(ns(age_c, knots = age_knots[2],
                          Boundary.knots = age_knots[c(1, 3)]))

  # logit P(Y <= j | X, u_s) = theta_j - (X beta + u_0s + u_1s * y0_c)
  # The inner solver for the random effects fails to converge if the
  # correlation between the two study terms is estimated, so they are
  # specified as independent.
  fixed <- eval(bquote(~ phq9_at_baseline_c + .(spline_term) + sex))
  full  <- eval(bquote(ordered(phq9_at_12mo) ~ phq9_at_baseline_c +
                         .(spline_term) + sex +
                         (1 | study_id) + (0 + phq9_at_baseline_c | study_id)))

  environment(fixed) <- env
  environment(full)  <- env
  list(fixed = fixed, full = full)
}


# -------------------------------- Fitting -----------------------------------
fit_risk_model <- function(df, formulas) {
  library(ordinal)

  fit <- clmm(formulas$full, data = df, link = "logit")

  # judge convergence against the log-likelihood scale
  rel_grad <- as.numeric(fit$info$max.grad) / abs(as.numeric(logLik(fit)))
  cat(sprintf("relative gradient = %.2e\n", rel_grad))
  if (rel_grad > 1e-3)
    warning("relative gradient is large - check convergence")

  fit
}


# ------------------------------- Prediction ---------------------------------
predict_phq9 <- function(model, newdata, type = c("link", "mean")) {

  type <- match.arg(type)

  missing_cols <- setdiff(c("y0", "age", "sex"), names(newdata))
  if (length(missing_cols))
    stop("newdata is missing: ", paste(missing_cols, collapse = ", "))

  newdata <- as.data.frame(newdata)

  # model.matrix drops incomplete rows
  incomplete <- !complete.cases(newdata[, c("y0", "age", "sex")])
  if (any(incomplete))
    stop(sum(incomplete), " of ", nrow(newdata), " row(s) have a missing ",
         "predictor (first at row ", which(incomplete)[1],
         "); predict_phq9 needs complete y0, age and sex")

  # constants for centering come from the fitted model
  newdata$phq9_at_baseline_c <- (newdata$y0 - model$scaling$y0_mu) / model$scaling$y0_sd
  newdata$age_c <- (newdata$age - model$scaling$age_mu) / model$scaling$age_sd

  unknown_sex <- setdiff(unique(as.character(newdata$sex)), model$sex_levels)
  if (length(unknown_sex))
    stop("sex value(s) not seen in development: ", paste(unknown_sex, collapse = ", "),
         "; expected ", paste(model$sex_levels, collapse = " or "))

  # stored levels keep the design matrix stable for a single-sex batch
  newdata$sex <- factor(as.character(newdata$sex), levels = model$sex_levels)

  # the instrument is bounded and anything outside is a data error
  if (any(newdata$y0 < 0 | newdata$y0 > 27, na.rm = TRUE))
    warning("y0 outside 0-27")

  # ages beyond the data rest on an assumption nothing can check
  n_outside_age_range <- sum(
    newdata$age < model$age_range[1] | newdata$age > model$age_range[2], na.rm = TRUE)
  if (n_outside_age_range)
    warning(n_outside_age_range, " of ", nrow(newdata),
            " ages outside the development range (",
            paste(round(model$age_range, 1), collapse = " to "), ")")

  design <- model.matrix(model$fixed_form, data = newdata)[, -1, drop = FALSE]

  if (nrow(design) != nrow(newdata))
    stop("model.matrix returned ", nrow(design), " rows for ", nrow(newdata),
         " patients")

  if (!identical(colnames(design), names(model$beta)))
    stop("design matrix does not match stored coefficients:\n  design: ",
         paste(colnames(design), collapse = ", "), "\n  beta:   ",
         paste(names(model$beta), collapse = ", "))

  # the risk score, with the study effect set to zero
  eta <- as.vector(design %*% model$beta)
  if (type == "link") return(eta)

  # P(Y <= j) at each threshold, then difference into one probability per score.
  # This is the mean for a patient in an average study, not the marginal mean
  # over studies: the two differ because the link is nonlinear.
  at_most <- sapply(model$thresholds, function(threshold) plogis(threshold - eta))
  if (is.null(dim(at_most))) at_most <- matrix(at_most, nrow = 1)
  exactly <- cbind(at_most, 1) - cbind(0, at_most)

  as.vector(exactly %*% model$ylevels)
}


# --------------------------------- Export -----------------------------------
export_risk_model <- function(fit, df, scaling, knots, formulas,
                              data_path = DATA_PATH, out_model = OUT_MODEL) {

  # clmm returns thresholds and slopes in one vector
  coefs        <- coef(fit)
  is_threshold <- grepl("\\|", names(coefs))

  # one VarCorr entry per study term, each holding a single SD
  study_sds <- unlist(lapply(ordinal::VarCorr(fit), function(v) attr(v, "stddev")))
  expected  <- c("study_id.(Intercept)", "study_id.phq9_at_baseline_c")
  if (!all(expected %in% names(study_sds)))
    stop("unexpected VarCorr layout: ", paste(names(study_sds), collapse = ", "))

  model <- list(
    thresholds = coefs[is_threshold],
    beta       = coefs[!is_threshold],
    fixed_form = formulas$fixed,
    age_knots  = knots,
    age_range  = range(df$age),
    scaling    = scaling,
    ylevels    = as.numeric(levels(ordered(df$phq9_at_12mo))),
    sex_levels = levels(df$sex),
    sigma0     = as.numeric(study_sds[expected[1]]),
    sigma1     = as.numeric(study_sds[expected[2]]),
    n_studies  = nlevels(droplevels(df$study_id)),
    n_dev      = nrow(df),
    cohort     = basename(dirname(data_path)),
    fitted_on  = Sys.Date(),
    r_version  = R.version.string
    # the fitted clmm object is not stored, it would carry the development data
  )

  dir.create(dirname(out_model), showWarnings = FALSE, recursive = TRUE)
  saveRDS(model, out_model)
  cat("wrote", out_model, "\n")

  invisible(model)
}

fit_and_export <- function(data_path = DATA_PATH, out_model = OUT_MODEL) {

  df       <- load_model_data(data_path)
  prepared <- add_centred_terms(df)
  df       <- prepared$data
  knots    <- age_spline_knots(df)
  formulas <- model_formulas(knots)

  cat("n =", nrow(df), " studies =", nlevels(droplevels(df$study_id)), "\n")

  fit <- fit_risk_model(df, formulas)
  print(summary(fit))

  model <- export_risk_model(fit, df, prepared$scaling, knots, formulas,
                             data_path, out_model)

  # try fitted model on three examples
  print("Predictions for three example patients:")
  reloaded <- readRDS(out_model)
  demo <- data.frame(y0  = c(5, 12, 20),
                     age = c(35, 55, 70),
                     sex = factor(c("Female", "Male", "Female"),
                                  levels = reloaded$sex_levels))
  print(data.frame(demo, eta = round(predict_phq9(reloaded, demo), 3)))

  invisible(model)
}

if (sys.nframe() == 0L && identical(commandArgs(trailingOnly = TRUE)[1], "fit"))
  fit_and_export()
