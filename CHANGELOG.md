# Changelog

All notable changes to `cochrane-modern-re` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- End-to-end analytical pipeline: loader → 4 methods (DL / REML_only / REML+HKSJ+PI / bayesmeta_HN) → 3-tier flip classifier → stratified aggregator → static HTML dashboard.
- Heuristic outcome-code mapper (`src/outcome_mapper.py`) for Tier 3 MID flip classification.
- MID lookup table (`data/mid_lookup.yaml`) covering 15 cardiology-focused outcomes + Cohen d = 0.2 SMD fallback.
- HKSJ Q/(k−1) floor enforcement (documented deviation from raw `metafor::rma(..., test="knha")`).
- Independent numerical validation harness (`src/validation.py` + `scripts/validation_reference.R`) at 1e-6 tolerance.
- CI: fast + slow + release tiers via GitHub Actions.
- Sentinel pre-push hook with BLOCK=0 scan at first install.
- Manuscript skeleton (`paper/manuscript.md`) targeting Research Synthesis Methods.
- Non-reproducible-subset results pinned in `paper/tables/non_reproducible/`.

### Known issues / deferred
- Full-corpus bayesmeta run deferred (~4 hrs compute); deterministic full-corpus is in progress.
- MID table coverage is ~10% of Cochrane outcomes — widen the mapping for higher Tier 3 coverage in v0.2.
- PET-PEESE and Copas publication-bias methods are out of scope for v0.1 (planned for follow-on paper).

## [0.1.0] — TBC (target: end 2026-Q2)

Initial demonstrator release. Headline results:

**Full corpus (6,386 loadable MAs from 7,545 parsed):**
- **Tier 1 significance flip (DL → REML+HKSJ+PI): 8.2%** (514 / 6,305 comparable)
- **Tier 2 direction flip: 0.6%** (36 / 6,305)
- **Tier 3 clinically-important flip: 3.9%** (27 / 688 MID-available subset)
- Deterministic-method convergence: 98.7% (REML_HKSJ_PI)

**Non-reproducible subset (680 MAs), 2× higher sensitivity:**
- Tier 1: 15.7%, Tier 2: 1.3%, Tier 3: 1.6% on MID-available

**Most-sensitive stratum:** continuous, k<5, non-reproducible = 23.3% Tier-1 flip rate (vs 1.8% for binary k≥20 reproducible).

**Bayesian comparator:** deferred to overnight run (~3 hrs compute at corpus scale).

Companion paper in preparation for Research Synthesis Methods.
