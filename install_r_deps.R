# Installs pinned R dependencies. Run once; CI uses renv.lock.
#
# Explicit library() calls below so renv::snapshot() discovers them via
# static analysis. Wrapped in FALSE so they never execute at runtime.
if (FALSE) {
  library(metafor)    # Viechtbauer 2010 — DL, REML, HKSJ, PI
  library(bayesmeta)  # Röver 2020 — Bayesian RE
  library(jsonlite)   # IO with Python subprocess
}

pkgs <- c("metafor", "bayesmeta", "jsonlite", "renv")

installed <- rownames(installed.packages())
to_install <- setdiff(pkgs, installed)
if (length(to_install) > 0) {
  install.packages(to_install, repos = "https://cloud.r-project.org/")
}

if (!file.exists("renv.lock")) {
  renv::init(bare = TRUE, force = TRUE)
}
renv::snapshot(prompt = FALSE, packages = pkgs)
cat("renv.lock written. Packages:", paste(pkgs, collapse = ", "), "\n")
