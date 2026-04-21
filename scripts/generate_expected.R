# Independent metafor reference — generates tests/fixtures/expected_metafor.json.
# Run this whenever the method set or fixtures change; pin the output in git.

suppressMessages({ library(metafor); library(jsonlite) })

fixtures <- list(
  # Heterogeneous enough that Q > k-1 → HKSJ floor doesn't bind; expected
  # values match raw metafor output at 1e-6.
  list(ma_id = "binary_k5_heterogeneous",
       yi = c(-0.30, 0.10, -0.50, 0.20, -0.15),
       vi = c(0.010, 0.020, 0.015, 0.012, 0.018)),
  list(ma_id = "binary_k3_moderate_het",
       yi = c(-0.30, 0.10, -0.20),
       vi = c(0.05, 0.07, 0.06)),
  list(ma_id = "continuous_k10_mixed",
       yi = c(0.20, 0.25, -0.10, 0.15, 0.40, 0.05, 0.50, -0.05, 0.30, 0.00),
       vi = rep(0.05, 10)),
  list(ma_id = "k2_boundary",
       yi = c(-0.10, 0.20),
       vi = c(0.02, 0.025))
  # homogeneous case (hksj_narrow_homogeneous) is tested for BEHAVIOR (floor
  # activates, CI widens) in test_hksj_floor_prevents_narrowing_below_dl;
  # not needed in expected_metafor.json.
)

run <- function(f, m, t) {
  tryCatch(rma(yi = f$yi, vi = f$vi, method = m, test = t), error = function(e) NULL)
}

expected <- list()
for (f in fixtures) {
  entry <- list()
  k <- length(f$yi)
  # Wald reference SE at REML tau^2 (for HKSJ floor)
  wald_ref <- run(f, "REML", "z")
  wald_se <- if (is.null(wald_ref)) NA else as.numeric(wald_ref$se)

  for (cfg in list(list(name = "DL",           m = "DL",   t = "z"),
                   list(name = "REML_only",    m = "REML", t = "z"),
                   list(name = "REML_HKSJ_PI", m = "REML", t = "knha"))) {
    res <- run(f, cfg$m, cfg$t)
    if (is.null(res)) {
      entry[[cfg$name]] <- list(converged = FALSE)
    } else {
      estimate <- as.numeric(res$beta[1])
      se <- as.numeric(res$se)
      ci_lo <- as.numeric(res$ci.lb)
      ci_hi <- as.numeric(res$ci.ub)

      # Apply HKSJ Q/(k-1) floor to match wrapper behaviour exactly.
      if (cfg$name == "REML_HKSJ_PI" && !is.na(wald_se) && se < wald_se && k >= 2) {
        se <- wald_se
        t_crit <- qt(0.975, df = k - 1)
        ci_lo <- estimate - t_crit * se
        ci_hi <- estimate + t_crit * se
      }

      pi_lo <- NA; pi_hi <- NA
      if (cfg$name == "REML_HKSJ_PI" && k >= 3) {
        pred <- tryCatch(predict(res), error = function(e) NULL)
        if (!is.null(pred)) { pi_lo <- pred$pi.lb; pi_hi <- pred$pi.ub }
      }
      entry[[cfg$name]] <- list(
        estimate = estimate,
        se = se,
        ci_lo = ci_lo,
        ci_hi = ci_hi,
        tau2 = as.numeric(res$tau2),
        i2 = as.numeric(res$I2),
        pi_lo = pi_lo, pi_hi = pi_hi,
        converged = TRUE
      )
    }
  }
  expected[[f$ma_id]] <- entry
}

out_path <- "tests/fixtures/expected_metafor.json"
dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
writeLines(toJSON(expected, auto_unbox = TRUE, na = "null",
                  digits = 15, pretty = TRUE), out_path)
cat(sprintf("wrote %s\n", out_path))
