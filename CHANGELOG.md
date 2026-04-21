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

Initial demonstrator release. Seed results:
- **Non-reproducible subset (680 MAs):** 15.7% Tier-1 significance flip, 1.3% Tier-2 direction flip, 1.6% Tier-3 MID flip (on 61 MID-available MAs).
- **Full corpus (7,545 MAs):** pending; see v0.1.0 release notes.

Companion paper in preparation for Research Synthesis Methods.
