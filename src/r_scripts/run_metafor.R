# run_metafor.R — DL / REML_only / REML_HKSJ_PI runner.
#
# Protocol (Python <-> R via stdio, JSON):
#   stdin:  {method: "DL"|"REML_only"|"REML_HKSJ_PI",
#            effect_scale: "logOR"|..., batch: [{ma_id, yi: [...], vi: [...]}, ...]}
#   stdout: [{ma_id, estimate, se, ci_lo, ci_hi, tau2, i2, pi_lo, pi_hi,
#             k_effective, converged, reason_code}, ...]
#
# HKSJ Q/(k-1) floor applied by metafor's test="knha" when rma() is called
# with that option (see metafor docs §rma `test`). PI at t_{k-2}; NA for k<3.

suppressMessages({
  library(jsonlite)
  library(metafor)
})

args <- fromJSON(file("stdin"), simplifyVector = FALSE)
method <- args$method
batch <- args$batch

null_result <- function(ma_id, k, reason) {
  list(ma_id = ma_id, estimate = NA_real_, se = NA_real_, ci_lo = NA_real_,
       ci_hi = NA_real_, tau2 = NA_real_, i2 = NA_real_, pi_lo = NA_real_,
       pi_hi = NA_real_, k_effective = k, converged = FALSE, reason_code = reason)
}

run_one <- function(one) {
  ma_id <- one$ma_id
  yi <- as.numeric(unlist(one$yi))
  vi <- as.numeric(unlist(one$vi))
  k <- length(yi)
  if (k < 2) return(null_result(ma_id, k, "k_too_small"))

  res <- tryCatch({
    if (method == "DL") {
      rma(yi = yi, vi = vi, method = "DL", test = "z")
    } else if (method == "REML_only") {
      rma(yi = yi, vi = vi, method = "REML", test = "z")
    } else if (method == "REML_HKSJ_PI") {
      # Fit with HKSJ; we'll audit & apply Q/(k-1) floor below.
      rma(yi = yi, vi = vi, method = "REML", test = "knha")
    } else {
      stop(sprintf("unknown method: %s", method))
    }
  }, error = function(e) NULL)

  if (is.null(res)) return(null_result(ma_id, k, "r_subprocess_error"))

  estimate <- as.numeric(res$beta[1])
  se_final <- as.numeric(res$se)
  ci_lo <- as.numeric(res$ci.lb)
  ci_hi <- as.numeric(res$ci.ub)

  # HKSJ Q/(k-1) floor (advanced-stats.md):
  # If Q/(k-1) < 1, HKSJ SE can be narrower than the REML+Wald SE. Set the floor
  # so HKSJ is never narrower than Wald. We refit with test="z" at the same REML
  # tau^2 to get the Wald SE, then take se_final = max(HKSJ_SE, Wald_SE) and
  # reconstruct CI with the HKSJ t-based critical value (df = k-1).
  if (method == "REML_HKSJ_PI" && k >= 2) {
    wald_ref <- tryCatch(rma(yi = yi, vi = vi, method = "REML", test = "z"),
                         error = function(e) NULL)
    if (!is.null(wald_ref)) {
      wald_se <- as.numeric(wald_ref$se)
      if (se_final < wald_se) {
        se_final <- wald_se
        # HKSJ uses t_{k-1} critical value; preserve that inference shape
        t_crit <- qt(0.975, df = k - 1)
        ci_lo <- estimate - t_crit * se_final
        ci_hi <- estimate + t_crit * se_final
      }
    }
  }

  pi_lo <- NA_real_; pi_hi <- NA_real_
  if (method == "REML_HKSJ_PI" && k >= 3) {
    pred <- tryCatch(predict(res), error = function(e) NULL)
    if (!is.null(pred)) {
      pi_lo <- as.numeric(pred$pi.lb)
      pi_hi <- as.numeric(pred$pi.ub)
    }
  }

  list(
    ma_id = ma_id,
    estimate = estimate,
    se = se_final,
    ci_lo = ci_lo,
    ci_hi = ci_hi,
    tau2 = as.numeric(res$tau2),
    i2 = as.numeric(res$I2),
    pi_lo = pi_lo,
    pi_hi = pi_hi,
    k_effective = k,
    converged = TRUE,
    reason_code = ""
  )
}

results <- lapply(batch, run_one)
cat(toJSON(results, auto_unbox = TRUE, na = "null", digits = 15))
