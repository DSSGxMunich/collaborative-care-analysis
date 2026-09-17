# PHQ-9 at 12 months: proportional-odds mixed model
#
#   fit    :  Rscript collaborative_care_analysis/data_analysis/risk_score_model.R fit
#   predict:  source(".../risk_score_model.R"); predict_phq9(readRDS(OUT_MODEL), newdata)
#
# newdata needs y0 (baseline PHQ-9), age (years) and sex.
# predict_phq9 returns eta, the risk score.

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
DATA_PATH <- file.path(REPO_ROOT, "data", "interim", "analysis_datasets", "phq9_12mo_core", "wide.csv")
OUT_MODEL <- file.path(REPO_ROOT, "models", "risk_score_model.rds")


# -------------------------------- Prediction --------------------------------
predict_phq9 <- function(model, newdata) {

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
  newdata$y0_c <- (newdata$y0  - model$scaling$y0_mu) / model$scaling$y0_sd
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

  age_knots <- model$age_knots
  design_formula <- model$fixed_form
  environment(design_formula) <- environment()
  design <- model.matrix(design_formula, data = newdata)[, -1, drop = FALSE]

  if (nrow(design) != nrow(newdata))
    stop("model.matrix returned ", nrow(design), " rows for ", nrow(newdata),
         " patients")

  if (!identical(colnames(design), names(model$beta)))
    stop("design matrix does not match stored coefficients:\n  design: ",
         paste(colnames(design), collapse = ", "), "\n  beta:   ",
         paste(names(model$beta), collapse = ", "))

  # the risk score, with the study effect set to zero
  as.vector(design %*% model$beta)
}

# -------------------------------- Fitting --------------------------------
fit_and_export <- function(data_path = DATA_PATH, out_model = OUT_MODEL) {

  library(data.table)
  library(ordinal)

  if (!file.exists(data_path))
    stop("no development data at ", data_path,
         "\nbuild it with: uv run collaborative_care_analysis/dataset.py analysis-data")

  raw_df <- fread(data_path, na.strings = c("", "NA"))

  df <- raw_df[, .(study = factor(STUDY_ID),
                   patient_id,
                   y     = phq9_total_outcome,
                   y0    = phq9_total_baseline,
                   age,
                   sex   = factor(sex))]
  df <- df[!is.na(y) & !is.na(y0) & !is.na(age) & !is.na(sex)]

  cat("n =", nrow(df), " studies =", nlevels(droplevels(df$study)), "\n")

  # centring constants, computed once here and carried in the model
  scaling <- list(y0_mu  = mean(df$y0),  y0_sd  = sd(df$y0),
                  age_mu = mean(df$age), age_sd = sd(df$age))

  df[, y0_c := (y0  - scaling$y0_mu)  / scaling$y0_sd]
  df[, age_c := (age - scaling$age_mu) / scaling$age_sd]

  # outer two are the boundary knots, inner two are interior
  age_knots <- as.numeric(quantile(df$age_c, c(0.05, 0.35, 0.65, 0.95)))
  spline_term <- quote(ns(age_c, knots = age_knots[2:3],
                          Boundary.knots = age_knots[c(1, 4)]))

  # logit P(Y <= j | X, u_s) = theta_j - (X beta + u_0s + u_1s * y0_c)
  # the inner solver for the random effects fails to converge if the
  # correlation between the two study terms is estimated
  fixed_form <- eval(bquote(~ y0_c + .(spline_term) + sex))
  full_form  <- eval(bquote(ordered(y) ~ y0_c + .(spline_term) + sex +
                              (1 | study) + (0 + y0_c | study)))

  fit <- clmm(full_form, data = df, link = "logit")
  print(summary(fit))

  # judge convergence against log-likelihood scale
  rel_grad <- as.numeric(fit$info$max.grad) / abs(as.numeric(logLik(fit)))
  cat(sprintf("relative gradient = %.2e\n", rel_grad))
  if (rel_grad > 1e-3)
    warning("relative gradient is large - check convergence")

  # clmm returns thresholds and slopes in one vector
  coefs        <- coef(fit)
  is_threshold <- grepl("\\|", names(coefs))

  # one VarCorr entry per study term, each holding a single SD
  study_sds <- unlist(lapply(VarCorr(fit), function(v) attr(v, "stddev")))
  if (!all(c("study.(Intercept)", "study.y0_c") %in% names(study_sds)))
    stop("unexpected VarCorr layout: ", paste(names(study_sds), collapse = ", "))

  model <- list(
    thresholds = coefs[is_threshold],
    beta       = coefs[!is_threshold],
    fixed_form = fixed_form,
    age_knots  = age_knots,
    age_range  = range(df$age),
    scaling    = scaling,
    ylevels    = as.numeric(levels(ordered(df$y))),
    sex_levels = levels(df$sex),
    sigma0     = as.numeric(study_sds["study.(Intercept)"]),
    sigma1     = as.numeric(study_sds["study.y0_c"]),
    n_studies  = nlevels(droplevels(df$study)),
    n_dev      = nrow(df),
    cohort     = basename(dirname(data_path)),
    fitted_on  = Sys.Date(),
    r_version  = R.version.string
    # the fitted clmm object is not stored, it would carry the development data
  )

  dir.create(dirname(out_model), showWarnings = FALSE, recursive = TRUE)
  saveRDS(model, out_model)
  cat("wrote", out_model, "\n")

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
