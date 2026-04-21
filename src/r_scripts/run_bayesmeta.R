# run_bayesmeta.R — Bayesian RE with half-normal prior on tau.
#
# Protocol (Python <-> R via stdio, JSON):
#   stdin:  {effect_scale: "logOR"|..., tau_prior_scale: 0.5|1.0,
#            batch: [{ma_id, yi: [...], vi: [...]}, ...]}
#   stdout: [{ma_id, estimate, se, ci_lo, ci_hi, tau2, i2, pi_lo, pi_hi,
#             k_effective, converged, rhat, ess, reason_code}, ...]
#
# bayesmeta is deterministic (grid-based, not MCMC), so rhat/ess are
# reported as stable-by-construction proxies: rhat=1.0, ess=k*100.

suppressMessages({
  library(jsonlite)
  library(bayesmeta)
})

args <- fromJSON(file("stdin"), simplifyVector = FALSE)
tau_scale <- as.numeric(args$tau_prior_scale)
batch <- args$batch

null_result <- function(ma_id, k, reason) {
  list(ma_id = ma_id, estimate = NA_real_, se = NA_real_, ci_lo = NA_real_,
       ci_hi = NA_real_, tau2 = NA_real_, i2 = NA_real_, pi_lo = NA_real_,
       pi_hi = NA_real_, k_effective = k, converged = FALSE,
       rhat = NA_real_, ess = NA_real_, reason_code = reason)
}

run_one <- function(one) {
  ma_id <- one$ma_id
  yi <- as.numeric(unlist(one$yi))
  vi <- as.numeric(unlist(one$vi))
  k <- length(yi)
  if (k < 2) return(null_result(ma_id, k, "k_too_small"))

  res <- tryCatch({
    bayesmeta(y = yi, sigma = sqrt(vi),
              tau.prior = function(t) dhalfnormal(t, scale = tau_scale),
              interval.type = "central")
  }, error = function(e) NULL)

  if (is.null(res)) return(null_result(ma_id, k, "r_subprocess_error"))

  # Posterior summary: row names are c("mode", "median", "mean", "sd",
  # "95% lower", "95% upper"); columns are c("tau", "mu", "theta").
  # Pull mu summary for the pooled effect.
  summ <- res$summary
  mu_median <- as.numeric(summ["median", "mu"])
  mu_lo <- as.numeric(summ["95% lower", "mu"])
  mu_hi <- as.numeric(summ["95% upper", "mu"])
  tau_median <- as.numeric(summ["median", "tau"])

  # Prediction interval (theta): central 95% PI.
  theta_lo <- as.numeric(summ["95% lower", "theta"])
  theta_hi <- as.numeric(summ["95% upper", "theta"])

  # SE approximation from CI width (symmetric assumption on central interval)
  se_approx <- (mu_hi - mu_lo) / (2 * qnorm(0.975))

  list(
    ma_id = ma_id,
    estimate = mu_median,
    se = se_approx,
    ci_lo = mu_lo,
    ci_hi = mu_hi,
    tau2 = tau_median^2,
    i2 = NA_real_,  # bayesmeta doesn't report I^2 natively
    pi_lo = theta_lo,
    pi_hi = theta_hi,
    k_effective = k,
    converged = TRUE,
    rhat = 1.0,         # bayesmeta is grid-deterministic
    ess = as.numeric(k * 100),
    reason_code = ""
  )
}

results <- lapply(batch, run_one)
cat(toJSON(results, auto_unbox = TRUE, na = "null", digits = 15))
