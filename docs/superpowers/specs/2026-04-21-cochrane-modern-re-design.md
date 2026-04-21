---
name: cochrane-modern-re — design spec
date: 2026-04-21
status: draft — pending user review
working-title: cochrane-modern-re
author: Mahmood Ahmad (mahmood726@gmail.com)
target-venue: Research Synthesis Methods (Wiley)
related-projects: repro-floor-atlas (v0.1.0, Synthēsis review pending), ma-workbench, ImpossibleMA, MetaAudit
---

# cochrane-modern-re — Design Spec

## 1. Purpose

Produce a demonstrator paper + reference implementation arguing that Cochrane's default RevMan methodology (DerSimonian-Laird random-effects with inverse-variance, no prediction interval, no HKSJ, no Bayesian alternative) materially changes clinical conclusions when replaced with modern equivalents. The paper answers: across ~7,500 published Cochrane pairwise meta-analyses, how often does modernising the RE method flip the significance, direction, or clinically-important-magnitude judgement of the pooled effect?

### Why this, why now

- `repro-floor-atlas` already established that 14.3% of Cochrane pairwise MAs fail numerical reproduction at |Δ|>0.005 (12.9% binary / 25.0% continuous / 27.0% GIV). That paper answers "can the result be reproduced?" — not "is the method defensible?"
- RevMan's statistical defaults are methodologically dated. REML > DL for k≥5, HKSJ with the Q/(k-1) floor dominates Wald CIs for small k, and prediction intervals (Higgins-Thompson-Spiegelhalter 2009) are now standard in RSM-adjacent literature.
- A solo-builder path to a Cochrane-adjacent contribution is a reference-implementation paper, not a workflow tool. This project is that paper.
- The differentiator vs. `repro-floor-atlas`: this paper measures the *downstream clinical impact* of the method choice, not the reproduction floor.

## 2. Scope

### In scope (v0.1)

- **Substrate:** `repro-floor-atlas` Pairwise70 cache — 7,545 pairwise Cochrane meta-analyses across 595 systematic reviews.
- **Methods compared (4):**
  1. `DL` — DerSimonian-Laird + Wald CI (RevMan baseline).
  2. `REML_only` — REML estimator + Wald CI (ablation to isolate estimator effect from inference-correction effect).
  3. `REML_HKSJ_PI` — REML + Hartung-Knapp-Sidik-Jonkman CI with `max(1, Q/(k-1))` floor + prediction interval using `t_{k-2}`. The headline comparator.
  4. `bayesmeta_HN` — `bayesmeta` Bayesian RE with half-normal prior on τ (scale = 0.5 for log-scale outcomes, 1.0 for SMD/MD), fallback to retry with `adapt_delta = 0.95` on non-convergence.
- **Flip tiers (3):**
  1. **Significance flip** (primary headline) — CI crosses null at α=0.05.
  2. **Direction flip** — sign of point estimate changes.
  3. **Clinically-important flip** — |Δ pooled effect| exceeds the MID for that outcome. Reported on the MID-available subset only; NA otherwise.
- **Analysis design:** Full 7,545-MA corpus as denominator; stratified by reproducibility status (from `repro-floor-atlas`), outcome type (binary / continuous / GIV), and k-stratum ({k<5, 5≤k<10, 10≤k<20, k≥20}). Staged execution: non-reproducible subset analysed first for fast-draft result, then expanded to full corpus.
- **Deliverables:**
  - Manuscript targeting Research Synthesis Methods (~5–7k words + figures + supplement).
  - Static HTML dashboard on GitHub Pages (single-file pattern matching `repro-floor-atlas`).
  - Full reproducibility package: `Dockerfile`, GitHub Actions CI replaying the full analysis, `requirements.txt` + `renv.lock`, tagged release archived to Zenodo with DOI.

### Out of scope (v0.1) — hard-locked

- No NMA, no DTA, no IPD meta-analyses.
- No screening, extraction, RoB 2 forms, GRADE SoF, PRISMA 2020 flow, CDSR XML round-trip.
- No multi-user features, no auth, no upload-your-own-data tool.
- No PET-PEESE, no Copas. Publication-bias methods are their own paper.
- No re-analysis of IPD; published effect sizes and SEs only.
- No Bayesian prior sensitivity sweep beyond the one specified half-normal. Sensitivity across priors is follow-on work.

### Post-publication plan

After acceptance: retire this repo into `repro-floor-atlas/modern_re/` as part of `repro-floor-atlas` v0.2.0. The Zenodo-DOI-archived snapshot remains the canonical citation for this paper.

## 3. Architecture

### Language split

- **Python 3.11+** — orchestration, data loading, flip classification, dashboard generation, CI glue. (3.13 avoided per `lessons.md` WMI deadlock rule.)
- **R 4.5.2** — method runners only: `metafor` (DL, REML, HKSJ, PI) and `bayesmeta` (Bayesian RE). Invoked via `subprocess → Rscript`, JSON stdin / JSON stdout. `rpy2` not used (Windows flakiness, bad for CI).

### Why the hybrid

`metafor` and `bayesmeta` are the reference implementations the RSM readership trusts. Re-implementing them in pure Python would require weeks of re-validation against those same R libraries. The subprocess boundary is ugly but correct, and it is isolated to `src/methods.py` and `src/r_scripts/`.

### Repo layout

```
cochrane-modern-re/
├── pyproject.toml
├── renv.lock
├── Dockerfile
├── .github/workflows/
│   ├── ci.yml          # fast + slow tier
│   └── validate.yml    # release tier (full-corpus numerical validation)
├── .sentinel.yml
├── README.md
├── data/
│   ├── pairwise70_cache/      # from repro-floor-atlas
│   └── mid_lookup.yaml
├── src/
│   ├── loaders.py
│   ├── methods.py             # Python orchestration, calls R
│   ├── r_scripts/
│   │   ├── run_metafor.R
│   │   └── run_bayesmeta.R
│   ├── flip_classifier.py
│   ├── aggregator.py
│   ├── dashboard.py
│   └── validation.py
├── tests/
│   ├── fixtures/
│   │   ├── pairwise70_smoke/  # 20-MA subset for integration
│   │   └── expected_metafor.json
│   ├── test_preflight.py
│   ├── test_contracts.py
│   ├── test_methods.py
│   ├── test_bayesmeta_mc.py
│   ├── test_flip_classifier.py
│   ├── test_aggregator.py
│   ├── test_integration.py
│   └── test_regression.py
├── analysis/
│   ├── 01_run_methods.py
│   ├── 02_classify_flips.py
│   ├── 03_aggregate.py
│   └── 04_build_dashboard.py
├── docs/                     # GitHub Pages root
│   └── index.html            # generated
├── paper/
│   ├── manuscript.md
│   ├── references.bib
│   └── tables/
└── outputs/                  # gitignored
```

### Key architectural choices

- **R subprocess batching** — one `Rscript` invocation per `(effect_scale × method)` group, not per MA. Invocation overhead dominates per-MA cost; batching brings full-corpus runtime to <30 min for the four deterministic methods and <90 min for Bayesian MCMC on the full corpus.
- **Caching** — per-MA method outputs stored as parquet, keyed by `(ma_id, method, config_hash)`. Re-runs after code changes only re-analyse affected MAs.
- **Single-file HTML dashboard** — pattern lifted from `repro-floor-atlas`. Embedded JSON, vanilla JS, no build step, no external CDN (per `rules.md` HTML apps section).
- **Two-tier CI** — fast tier (<120 s) gates every push; slow tier (~15 min) gates PRs to `main`; release tier (~90 min) gates tags. Compute budgets match the `rules.md` preflight-readiness timing rules.

## 4. Components

### 4.1 `loaders.py`

- Input: `pairwise70_cache/` directory.
- Output: iterator of `MA` records — `{ma_id, review_id, outcome_type, outcome_code, effect_scale, studies: [(yi, vi)], k, reproducibility_status}`.
- Effect scales: `logRR`, `logOR`, `logHR` (binary); `SMD`, `MD` (continuous); `GIV` (generic inverse variance). Ratio measures pooled on log scale always (per `advanced-stats.md`).
- Carries `reproducibility_status` through from `repro-floor-atlas` so downstream stratification does not recompute it.

### 4.2 `methods.py` + `r_scripts/`

- Input: batch of MAs (grouped by `effect_scale`), method name.
- Output: for each MA — `{ma_id, method, estimate, se, ci_lo, ci_hi, tau2, i2, pi_lo, pi_hi, k_effective, converged, rhat, ess, reason_code}`.
- Four methods implemented (DL, REML_only, REML_HKSJ_PI, bayesmeta_HN).
- R subprocess: JSON in via stdin, JSON out via stdout. Non-zero exit + retry + hard-fail on second failure.

### 4.3 `flip_classifier.py`

- Input: two method outputs for the same `ma_id` (baseline + comparator) + MID lookup table.
- Output: `{tier1_sig_flip, tier2_direction_flip, tier3_mid_flip}` where each is `bool | NA`.
- **Tier 1** — `sign(ci_lo × ci_hi)` change. Positive product → does not cross null; negative product → crosses null. Flip = change in that status.
- **Tier 2** — `sign(estimate)` change.
- **Tier 3** — scale-aware: for ratio outcomes (`logRR`/`logOR`/`logHR`) both estimates are back-transformed to natural scale before comparison (`|exp(est_base) - exp(est_comp)| > mid`). For continuous outcomes (`SMD`/`MD`/`GIV`) the comparison is direct (`|est_base - est_comp| > mid`). `NA` if outcome not in MID table.
- MID table: YAML keyed by `outcome_code`, with each entry specifying `{mid: <value>, scale: <"natural"|"sd_units">, source: <citation>}`. ~15 well-established outcomes at v0.1: all-cause mortality (natural-scale RR Δ = 0.05), MACE (RR Δ = 0.05), HF hospitalisation (RR Δ = 0.05), common QoL MCIDs per instrument, SMD = 0.2 (Cohen "small") as fallback for SMD outcomes with no published MID. Extensible. MID values for v0.1 are sourced and reviewed at plan stage (see §9).

### 4.4 `aggregator.py`

- Input: flip classifications per MA.
- Output: cross-tab dataframes keyed by `(reproducibility_status × outcome_type × k_stratum × comparison_pair × flip_tier)`.
- Produces headline + supplementary tables as parquet AND markdown (for direct inclusion in `paper/tables/`).
- k-strata: `{k<5, 5≤k<10, 10≤k<20, k≥20}`. The first two are where DL bias is worst (per `advanced-stats.md`).
- Reports both denominators: `(flips / comparable_MAs)` and `(flips / total_MAs)`. Missing-data attrition is its own supplementary table.

### 4.5 `dashboard.py`

- Reads aggregator output + per-MA method outputs.
- Writes `docs/index.html`.
- Views: summary flip-rate table (top), per-outcome-type breakdown, per-MA drill-down with 4-method forest-plot comparison, method-convergence diagnostics.
- Pattern lifted from `repro-floor-atlas`. Fully offline-capable, no external CDN.

### 4.6 `validation.py`

- Compares deterministic method outputs against an independent `metafor` reference invocation (written by a different author/agent than `run_metafor.R`) at `1e-6` tolerance.
- Bayesian validation: `atol = 0.05`, 3σ bounds, seeded, 5 runs per fixture (per `advanced-stats.md` Monte Carlo rule).
- Runs as a separate CI job; blocks release-tier promotion on any tolerance failure.

## 5. Data Flow

```
Pairwise70 cache ──► loaders ──► MA stream (7,545)
                                      │
                                      ▼
                            methods.py (batched by scale)
                                      │
                       ┌──────────────┼──────────────┐
                       ▼              ▼              ▼
                    DL result    REML+HKSJ+PI    bayesmeta
                       │              │              │
                       └──────────────┼──────────────┘
                                      ▼
                              merge per ma_id
                                      │
                                      ▼
                         flip_classifier (+ MID lookup)
                                      │
                                      ▼
                                aggregator
                                      │
                      ┌───────────────┴───────────────┐
                      ▼                               ▼
               dashboard (HTML)              paper/tables (markdown)
```

## 6. Error Handling & Edge Cases

**At load time:**
- Missing SE / effect → skip with reason `insufficient_data`.
- Negative `vi` → skip with reason `invalid_variance`; loud log.
- Duplicate `ma_id` → hard fail with reason `dataset_integrity_error`.
- Unknown `outcome_code` → log warning; `tier3_mid = NA` for this MA.
- Encoding → UTF-8 explicit; BOM stripped; fail-closed on decode errors (never `errors='replace'`).

**At method-runner time:**
- `k < 2` → all methods NA; reason `k_too_small`.
- `k < 3` and method = `REML_HKSJ_PI` → PI returned as NA (undefined at `t_{k-2}`); point estimate and HKSJ CI retained. No fallback to `t_{k-1}`.
- `k < 10` and method = `DL` → run anyway (it's the baseline); tag `dl_biased_warning: true`. Disclosed in paper methods section.
- HKSJ `Q/(k-1) < 1` → apply floor `max(1, Q/(k-1))` per `advanced-stats.md`. Unit tested against hand-computed case.
- Zero cells (2×2 binary) → add 0.5 only if ≥1 cell is zero. Never unconditional.
- `tau2 = 0` → accept result; tag `tau2_zero: true`. PI returned as NA.
- Bayesian non-convergence (`Rhat > 1.01 OR ESS < 400`) → retry once with 2× iterations and `adapt_delta = 0.95`. If still unconverged → `{converged: false}`; exclude from aggregator; surface in diagnostics dashboard.
- R subprocess non-zero exit → capture stderr; retry once; then hard-fail the entire batch with reason `r_subprocess_error`. No silent partial results.
- R subprocess timeout → 5 min hard cap per batch; timeout routed to the same error path as non-zero exit.
- Log-scale numerical overflow → use `exp(a) * (1 + exp(b-a))` per `lessons.md`. Never `exp(a) + exp(b)` raw.

**At flip-classifier time:**
- MID not in lookup → `tier3 = NA`, not `false`.
- Baseline or comparator NA → flip = NA with reason `comparison_unavailable`.
- Baseline converged but comparator didn't → flip = NA with reason `comparator_unconverged`. Do not claim agreement where the comparator actually failed.

**At aggregator time:**
- Always report both denominators: `(flips / comparable_MAs)` AND `(flips / total_MAs)`.
- k-stratum with n < 20 → report rate but tag `sparse_stratum: true` in dashboard tooltip; do not suppress.

**At dashboard time:**
- Every `.iloc[0]` / `.iloc[-1]` / `.values[0]` access guarded per `lessons.md` P1-empty-dataframe-access rule. Sentinel enforces.

**Validation failure handling:**
- Any method drift beyond `1e-6` (deterministic) or 3σ (Bayesian) → CI fails; release blocked until resolved.

**Release-gate Sentinel rules enabled:**
- No hardcoded local paths.
- No placeholder HMAC / forgeable signature artifacts.
- No committed `.claude/` configs.
- Empty-DataFrame-access check (P1-empty-dataframe-access).
- Top-5 Cross-Project Defects checks from `lessons.md`.
- `SENTINEL_BYPASS` logged to `~/.sentinel-logs/bypass.log` if used.

**Overall posture:** fail-closed. When in doubt, emit NA with a reason code rather than a silent fallback. The aggregator sees all reason codes and reports them in a supplementary attrition table — this is itself a methodological talking point in the paper.

## 7. Testing Strategy

### 7.1 Test pyramid

1. **Preflight** (`tests/test_preflight.py`) — R 4.5.2 importable; `metafor` + `bayesmeta` loadable; `Rscript` subprocess invokable with UTF-8 stdout; Pairwise70 cache path resolves; MID YAML parses.
2. **Contract tests** (`tests/test_contracts.py`) — written FIRST per `lessons.md`. One test per module boundary (`loader→methods`, `methods→flip_classifier`, `flip_classifier→aggregator`). Assert outputs are not silent-failure sentinels.
3. **Unit — method correctness** (`tests/test_methods.py`) — 10 hand-picked Cochrane MA fixtures covering binary (k=3,5,10,20), continuous (SMD, MD), GIV, and edge cases (k=2 required, one zero-cell, one tau²=0). Expected values from direct `metafor` calls recorded in `fixtures/expected_metafor.json`. All deterministic outputs matched at `1e-6`.
4. **Unit — Bayesian Monte Carlo** (`tests/test_bayesmeta_mc.py`) — seeded, 3 fixtures × 5 runs each. `atol = 0.05`, 3σ bounds. One test asserts Rhat > 1.01 triggers retry; one asserts non-convergence after retry produces `{converged: false}` not a stale estimate.
5. **Unit — flip classifier** (`tests/test_flip_classifier.py`) — 12 hand-coded cases across every tier combination, including the important `(T1=F, T2=F, T3=T)` case (clinical flip without significance flip). One test per `tier3 = NA` path.
6. **Unit — aggregator** (`tests/test_aggregator.py`) — 50-MA fixture with known flip-rate totals; cross-tab matches hand-computed; sparse-stratum flag engages; both denominators reported.
7. **Integration** (`tests/test_integration.py`) — 20-MA smoke fixture (committed); runs `analysis/01..04` in sequence; asserts dashboard HTML produced and flip-rate JSON matches pinned baseline. Runtime budget <120 s.
8. **Regression snapshots** (`tests/test_regression.py`) — top-level flip rates pinned per release in `snapshots/flip_rates_v0.1.0.json`. Change >2% = regression, CI fails (per `rules.md` snapshot rule).
9. **Validation harness** (`src/validation.py` via `.github/workflows/validate.yml`) — full-corpus DL output vs. independent `metafor` direct-call script. Runs on `main` pushes and tags only.

### 7.2 CI structure

- **Fast tier** (every push, <120 s): preflight + unit + contract + 20-MA integration.
- **Slow tier** (PRs to `main`, ~15 min): adds Bayesian Monte Carlo + 100-MA integration + regression snapshots.
- **Release tier** (tags, ~90 min): full-corpus validation harness + dashboard build + Zenodo artifact upload.

### 7.3 Coverage target

- 90% line coverage on `src/`.
- `analysis/` scripts excluded (covered via integration).
- `r_scripts/` excluded (covered via `test_methods.py` + validation harness).

### 7.4 Ship gates (all green required to tag a release)

1. All fast + slow + release tests pass.
2. Validation harness: no method drift beyond tolerance.
3. Sentinel: zero BLOCK findings.
4. Regression snapshots unchanged (or explicitly bumped with rationale in the release notes).

## 8. Timeline & Milestones (indicative)

- **Week 0** — Spec approved, implementation plan written (via `writing-plans`).
- **Week 1** — Repo scaffolded; Python + R environment; preflight + contract tests green; loader + method runners functional on 20-MA fixture.
- **Week 2** — Flip classifier + aggregator; non-reproducible-subset analysis (1,080 MAs) complete end-to-end; first-cut dashboard.
- **Week 3** — Full corpus analysis (7,545 MAs); stratified tables; Bayesian method convergence audit.
- **Week 4** — Validation harness green; paper first draft (methods + results); dashboard polish.
- **Week 5** — Paper review cycle (self, then at least one external methodologist); revision.
- **Week 6** — Submission to Research Synthesis Methods; Zenodo DOI minted; repo tagged v0.1.0.

Total: ~6 weeks for v0.1.0 tag + submission. Slipping to 8 weeks is acceptable; beyond that, re-scope.

## 9. Open questions (for implementation plan to resolve)

- Exact MID values for the initial 15 outcomes — to be sourced from published MCID papers and reviewed by MA during implementation plan stage.
- Final name — `cochrane-modern-re` is the working title; consider also `revman-flip-atlas`, `pairwise-modernization`. Decision deferred to plan kickoff.
- Authorship and CRediT — per `feedback_e156_authorship.md`, MA is middle-author-only on Synthēsis submissions; RSM is not Synthēsis so MA could be first/last, but this is the user's call at plan stage.

## 10. Related work / references (for later)

- Higgins JPT, Thompson SG, Spiegelhalter DJ (2009). A re-evaluation of random-effects meta-analysis. JRSS A 172:137–159.
- IntHout J, Ioannidis JPA, Borm GF (2014). The Hartung-Knapp-Sidik-Jonkman method for random effects meta-analysis is straightforward and considerably outperforms the standard DerSimonian-Laird method. BMC MRM 14:25.
- Röver C (2020). Bayesian random-effects meta-analysis using the bayesmeta R package. J Stat Softw 93(6).
- Viechtbauer W (2010). Conducting meta-analyses in R with the metafor package. J Stat Softw 36(3).
- `repro-floor-atlas` v0.1.0 — Ahmad M (2026), Synthēsis submission (under review).
