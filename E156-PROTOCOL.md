# E156 Protocol — cochrane-modern-re

<!-- sentinel:skip-file  (E156 convention: the PATH: metadata line below is
     intentional provenance, not deployed code. Mirrors the marker at the
     head of C:\E156\rewrite-workbook.txt.) -->

**Project:** cochrane-modern-re
**Title:** Modern Random-Effects Methods Change the Significance Judgement of Cochrane Pairwise Meta-Analyses in 8.2% of Cases
**Type:** methods
**Primary estimand:** Tier-1 significance-flip rate (DL → REML+HKSJ+PI) across Cochrane pairwise meta-analyses
**Data:** Pairwise70 corpus — 582 Cochrane reviews; 6,386 loadable pairwise meta-analyses; reproducibility status merged from repro-floor-atlas `outputs/atlas.csv`
**Path:** `C:\Projects\cochrane-modern-re`
**Repo:** https://github.com/mahmood726-cyber/cochrane-modern-re
**Tag at submission:** `v0.1.0`
**Dashboard:** https://mahmood726-cyber.github.io/cochrane-modern-re/
**Zenodo DOI:** [TBC at mint]

## E156 body (156-word, 7-sentence structure)

Does modernising RevMan's random-effects defaults from DL to REML+HKSJ with a prediction interval change the significance judgement of Cochrane pairwise meta-analyses? We re-analysed 6,386 loadable pairwise meta-analyses from 582 Cochrane reviews in the Pairwise70 corpus via the MetaAudit loader. For each meta-analysis we compared DL against REML+HKSJ+PI with a Q/(k−1) floor and classified three flip tiers (significance, direction, clinically-important). Across the full corpus 8.2% of comparable meta-analyses flipped significance, 0.6% flipped direction, and 3.9% of the MID-available subset exceeded the clinically-important threshold. The effect concentrated in small-k and non-reproducible reviews; non-reproducible meta-analyses were approximately twice as method-sensitive as reproducible ones at every stratum examined. Method choice alone changes the significance judgement in roughly one in twelve Cochrane pairwise reviews, with the largest effect in continuous small-k analyses. Findings apply to aggregate pairwise data only; network meta-analyses, IPD reanalysis, and publication-bias methods are out of scope for v0.1.

## Methodological notes

- **HKSJ Q/(k−1) floor** — `metafor::rma(..., test="knha")` does not apply this floor natively; we enforce it by comparing the HKSJ SE against the REML+Wald SE at the same τ² and taking the larger, then reconstructing the CI with the *t*_{k−1} critical value.
- **Tier 3 scale-awareness** — ratio outcomes (logRR/logOR/logHR) are back-transformed before the |Δ| vs MID comparison; continuous outcomes (SMD/MD/GIV) are compared directly on the analysis scale.
- **MID coverage** — `data/mid_lookup.yaml` covers 15 cardiology-focused outcomes + Cohen d = 0.2 SMD fallback. A heuristic regex mapper (`src/outcome_mapper.py`, 17 tests) links free-text Cochrane `Analysis.name` labels to MID keys; the remainder map to `unknown_outcome` and are marked NA for Tier 3.
- **Bayesmeta comparator** — half-normal prior on τ (scale = 0.5 for log-scale outcomes, 1.0 for SMD/MD/GIV). Deterministic grid-based so rhat = 1.0; reported on the smoke subset only in v0.1 (full-corpus run deferred to ~3–4 hrs overnight compute).
- **Independent validation** — `src/validation.py` + `scripts/validation_reference.R` cross-check DL and REML_only outputs against raw `metafor` at 1e-6 tolerance. HKSJ deliberately excluded (our wrapper floors, raw metafor doesn't); HKSJ correctness is validated behaviourally in `tests/test_methods.py::test_hksj_floor_prevents_narrowing_below_dl`.

## Reproducibility

```bash
docker build -t cochrane-modern-re .
docker run --rm -v $(pwd):/work cochrane-modern-re python -m pytest
```

Full-corpus analysis (deterministic methods only, ~12 min on Mahmood's dev box):

```bash
cp src/paths_local.example.py src/paths_local.py  # edit for your env
python scripts/prereq_check.py
python analysis/01_run_methods.py --skip-bayes --out outputs/full_method_results.parquet
python analysis/02_classify_flips.py --method-results outputs/full_method_results.parquet --out outputs/flips.parquet
python analysis/03_aggregate.py --flips outputs/flips.parquet --out-dir outputs --tables-dir paper/tables
python analysis/04_build_dashboard.py --out docs/index.html --version 0.1.0
python -m src.validation
```

## Key numbers (v0.1.0 snapshot)

| Tier | Rate | n |
|---|---|---|
| 1 — Significance flip | **8.2%** | 514 / 6,305 comparable |
| 2 — Direction flip | 0.6% | 36 / 6,305 |
| 3 — Clinically-important flip | 3.9% | 27 / 688 MID-available |

**Non-reproducible subset (680 MAs):** 15.7% Tier-1 — approximately 2× the full-corpus rate at every (outcome × k-stratum) cell.

**Extreme cells:**
- Most sensitive: continuous, k<5, non-reproducible → **23.3%**
- Least sensitive: binary, k≥20, reproducible → **1.8%**

## Tests + CI

- 94 tests passing locally (63 on CI; 31 require external Pairwise70 data and skip gracefully).
- Sentinel: BLOCK=0 WARN=0.
- CI: fast tier (master push, every commit), slow tier (PRs to master), release tier (tags).

## Related projects

- [`repro-floor-atlas`](https://github.com/mahmood726-cyber/repro-floor-atlas) — provides the numerical-reproduction floor and `atlas.csv` input.
- [`MetaAudit`](https://github.com/mahmood726-cyber/MetaAudit) — `.rda` loader + per-study recompute used here.
- After v0.1.0 publication this project will be folded into `repro-floor-atlas/modern_re/` for its v0.2.0.
