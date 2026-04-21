# validation_reference.R — Independent metafor reference.
#
# Deliberately written differently from src/r_scripts/run_metafor.R to catch
# systematic drift: this script calls rma.uni() directly with minimal options
# and does NO floor/audit logic. It produces raw metafor DL and REML_only
# output; HKSJ is deliberately EXCLUDED because the wrapper applies a floor
# that raw metafor doesn't. HKSJ behavior is validated behaviourally in
# tests/test_methods.py::test_hksj_floor_prevents_narrowing_below_dl.
#
# Protocol:
#   stdin:  {batch: [{ma_id, yi, vi}, ...]}
#   stdout: [{ma_id, dl_est, dl_se, reml_est, reml_se, reml_tau2}, ...]

suppressMessages({ library(metafor); library(jsonlite) })

args <- fromJSON(file("stdin"), simplifyVector = FALSE)
batch <- args$batch

results <- vector("list", length(batch))
for (i in seq_along(batch)) {
  one <- batch[[i]]
  yi <- as.numeric(unlist(one$yi))
  vi <- as.numeric(unlist(one$vi))
  k <- length(yi)
  if (k < 2) {
    results[[i]] <- list(ma_id = one$ma_id, dl_est = NA, dl_se = NA,
                          reml_est = NA, reml_se = NA, reml_tau2 = NA)
    next
  }
  dl <- tryCatch(rma.uni(yi, vi, method = "DL"), error = function(e) NULL)
  reml <- tryCatch(rma.uni(yi, vi, method = "REML"), error = function(e) NULL)
  results[[i]] <- list(
    ma_id = one$ma_id,
    dl_est = if (is.null(dl)) NA else as.numeric(coef(dl)),
    dl_se = if (is.null(dl)) NA else as.numeric(dl$se),
    reml_est = if (is.null(reml)) NA else as.numeric(coef(reml)),
    reml_se = if (is.null(reml)) NA else as.numeric(reml$se),
    reml_tau2 = if (is.null(reml)) NA else as.numeric(reml$tau2)
  )
}
cat(toJSON(results, auto_unbox = TRUE, na = "null", digits = 15))
