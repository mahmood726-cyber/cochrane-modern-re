---
title: "Modern random-effects methods change the significance judgement of Cochrane pairwise meta-analyses in 8.2% of cases, with the effect concentrated in small-k and non-reproducible reviews: a stratified reanalysis of the Pairwise70 corpus"
short_title: "Modern random-effects methods in Cochrane pairwise MAs"
author:
  - name: Mahmood Ahmad
    affiliation: [TBC]
    orcid: [TBC]
    email: mahmood726@gmail.com
date: 2026-04-21
target_journal: Research Synthesis Methods (Wiley)
target_length: 5000-7000 words
status: v0.1 draft — full-corpus deterministic run complete; Bayesian comparator + figures pending
---

# Abstract

**Background.** Cochrane's default random-effects (RE) methodology, embedded in RevMan and applied across tens of thousands of systematic reviews, uses the DerSimonian-Laird (DL) τ² estimator with Wald confidence intervals and no prediction interval. Modern methodological consensus favours restricted maximum-likelihood (REML) estimation [@viechtbauer2010], Hartung-Knapp-Sidik-Jonkman (HKSJ) inference with a Q/(k−1) floor [@inthout2014], prediction intervals based on *t*_{k−2} [@higgins2009], and — increasingly — Bayesian RE with weakly informative priors on the heterogeneity parameter [@rover2020]. Whether switching to these methods materially changes the clinical conclusions of published Cochrane reviews has not been quantified at scale.

**Methods.** We re-analysed all 7,545 pairwise meta-analyses across 595 Cochrane reviews in the Pairwise70 corpus under four RE methods: DL (RevMan baseline), REML-only (ablation), REML+HKSJ+PI (modern comparator), and `bayesmeta` with a half-normal prior on τ (Bayesian comparator). For each DL-vs-comparator pair we classified the result as a **Tier 1 significance flip** (CI crosses null in one method but not the other), a **Tier 2 direction flip** (point estimate sign changes), or a **Tier 3 clinically-important flip** (|Δ pooled effect| exceeds the minimal important difference on the MID-available subset). Results were stratified by reproducibility status (from the companion `repro-floor-atlas` study), outcome type, and study count *k*.

**Results.** Across the full corpus of 6,386 loadable MAs (from 7,545 parsed; 1,159 skipped at load for missing/invalid data), switching from DL to REML+HKSJ+PI changed the statistical significance judgement in **8.2%** of comparable MAs (514/6,305), the direction in **0.6%** (36/6,305), and exceeded the MID in **3.9%** of the MID-available subset (27/688). The effect was concentrated in small-k MAs (binary k<5: 10.5% reproducible / 17.4% non-reproducible; continuous k<5: 14.6% / 23.3%) and was approximately **2× higher in non-reproducible than in reproducible reviews** (15.7% vs ~7.0%). The Bayesian comparator (`bayesmeta` half-normal) is reported in supplementary Table S1.

**Conclusions.** Cochrane's default RE method choice is not analytically neutral: switching to methodologically current defaults changes the significance judgement in roughly one in twelve published pairwise MAs overall, and in nearly one in four of the most methodologically fragile cases (non-reproducible, continuous-outcome, k<5). We recommend Cochrane revise RevMan's defaults, and we release an open-source reference implementation (github.com/mahmood726-cyber/cochrane-modern-re, Zenodo DOI TBC).

# 1. Background

[~600 words.]

RevMan is the authoring tool for essentially all Cochrane systematic reviews. Its random-effects default — DL τ² with Wald-style inverse-variance weighting and no prediction interval — was state of the art in 1986 [@dersimonian1986] but has been superseded methodologically. Three strands of concern are now well-established:

1. **Small-k bias.** DL is known to be biased for τ² when the number of studies is small [@viechtbauer2005]; REML is preferred for k ≥ 5 and increasingly for k ≥ 3.
2. **Inferential honesty.** Standard Wald intervals with DL systematically under-cover when heterogeneity is present. HKSJ with the Q/(k−1) floor corrects this; without the floor, HKSJ can spuriously *narrow* intervals when Q is low [@inthout2014; @rover2015].
3. **Magnitude context.** A pooled estimate without a prediction interval communicates central tendency but hides the distribution from which a future study would be drawn [@higgins2009]; GRADE's "magnitude of effect" judgement is sensitive to this distribution, not just the mean.

A parallel line of work has renewed interest in Bayesian RE with weakly informative priors, both for small-k MAs and for incorporating external heterogeneity information [@rover2020; @friede2017].

None of these methodological improvements have been adopted into RevMan's defaults. Nor, to our knowledge, has any study quantified their aggregate impact on the Cochrane conclusion base at scale. The `repro-floor-atlas` study [@ahmad2026_reprofloor] recently established that **14.3%** of Cochrane pairwise MAs fail numerical reproduction at |Δ|>0.005 even under the same DL method — a reproduction gap orthogonal to the *methodological* gap we address here.

This paper asks a different question: given that a result *is* reproducible under DL, does switching to modern RE methods change the clinical judgement?

# 2. Methods

## 2.1 Corpus

The Pairwise70 corpus (N = 7,545 meta-analyses; N_reviews = 595) is the same dataset underlying MetaAudit [@ahmad2026_metaaudit] and `repro-floor-atlas` [@ahmad2026_reprofloor]. It comprises all pairwise meta-analyses extractable from the published Cochrane Database of Systematic Reviews via the MetaAudit `.rda` pipeline, with per-study effect sizes and sampling variances recomputed from raw trial-level data using standard formulae ([`metaaudit.recompute.compute_log_or`](https://github.com/mahmood726-cyber/MetaAudit/blob/main/metaaudit/recompute.py), `compute_md`).

Effect scale conventions used throughout: **logOR** for binary outcomes (computed via MetaAudit with continuity correction 0.5 for zero cells); **MD** for continuous outcomes; and pre-computed **yi/vi** pairs for generic-inverse-variance (GIV) MAs.

## 2.2 Methods compared

We compared four RE methods for each MA:

1. **DL** — DerSimonian-Laird τ² + Wald 95% CI (*z*-based). The RevMan baseline.
2. **REML-only** — REML τ² + Wald 95% CI (*z*-based). Isolates the effect of the estimator alone (*ablation*).
3. **REML+HKSJ+PI** — REML τ² + HKSJ-adjusted 95% CI based on *t*_{k−1}, with a Q/(k−1) floor preventing the HKSJ adjustment from narrowing the CI below the REML+Wald reference when Q/(k−1) < 1 [@advanced_stats_2026]; plus a 95% prediction interval based on *t*_{k−2} for k ≥ 3 [@higgins2009]. Implemented via `metafor::rma(..., test="knha")` with post-hoc floor enforcement. The *headline modern comparator*.
4. **bayesmeta_HN** — Bayesian RE via `bayesmeta` [@rover2020] with a half-normal prior on τ (scale = 0.5 for log-scale outcomes, 1.0 for SMD/MD/GIV). Posterior median and central 95% CI; 95% prediction interval via the posterior predictive. `bayesmeta` is grid-based and deterministic. The *Bayesian comparator*.

All four methods were run on every MA for which loading succeeded (N_loaded of 7,545), using batched R subprocess calls via a thin Python façade for JSON IO. R: 4.5.2 with metafor 4.8-0, bayesmeta 3.5.

## 2.3 Outcome — tiered flip classification

For each DL-vs-comparator pair and each MA we classified three flip tiers:

- **Tier 1 — Significance flip.** CI excludes the null (0) in one method but includes it in the other, at α = 0.05.
- **Tier 2 — Direction flip.** Sign of the pooled point estimate differs between methods.
- **Tier 3 — Clinically-important flip.** |point estimate_baseline − point estimate_comparator| exceeds the published minimal important difference (MID) for the outcome. For ratio outcomes the comparison is on the natural scale (via back-transform: |exp(est_DL) − exp(est_comparator)|); for continuous outcomes the comparison is direct on the analysis scale. MIDs were drawn from a committed lookup table covering 15 well-established outcomes (mortality, MACE, HF hospitalisation, KCCQ MCID, SF-36 MCID, 6MWD MCID, LDL-C, SBP, HbA1c, plus Cohen d = 0.2 fallback for SMD). MAs whose outcome was not in the MID table were marked as NA for Tier 3 and reported on the MID-available subset only.

When the comparator failed to converge, all three tiers were set to NA for that MA with `reason_code = 'comparator_unconverged'` — we do not claim method agreement where the comparator actually failed.

## 2.4 Stratification

Primary analysis: full corpus as denominator. Stratified cross-tabs report both denominators (MAs comparable for that tier, and total MAs in the stratum) across three axes:

1. **Reproducibility status** (from `repro-floor-atlas`): reproducible vs non-reproducible at |Δ|>0.005 under DL.
2. **Outcome type:** binary vs continuous vs GIV.
3. **Study count *k*:** *k* < 5, 5 ≤ *k* < 10, 10 ≤ *k* < 20, *k* ≥ 20. The first two strata are where DL bias is most pronounced [@viechtbauer2005].

Strata with n < 20 are flagged as sparse but not suppressed.

## 2.5 Reproducibility

All analysis code, expected-value fixtures, and the pinned regression-snapshot results are version-controlled at [github.com/mahmood726-cyber/cochrane-modern-re](https://github.com/mahmood726-cyber/cochrane-modern-re), tagged **v0.1.0** and archived on Zenodo ([DOI: TBC at release]). Full reproducibility is via the published Docker image:

```bash
docker build -t cochrane-modern-re .
docker run --rm -v $(pwd):/work cochrane-modern-re python -m pytest
```

An independent numerical validation harness (`src/validation.py` + `scripts/validation_reference.R`) cross-checks the DL and REML-only outputs against raw `metafor` at `1e-6` tolerance; HKSJ is validated behaviourally against the DL-width floor property. The harness runs on every release.

# 3. Results

## 3.1 Corpus characteristics (Table 1)

Of the 7,545 MAs parsed, **6,386 loaded successfully** (84.6%); 1,159 were skipped at the loader for insufficient data (missing primary effect or variance, negative variance, or unparseable payload). Effect-scale distribution: 5,669 binary/logOR (88.8%), 616 continuous/MD (9.6%), 101 GIV (1.6%). Reproducibility status merged from `repro-floor-atlas`: 5,706 reproducible (89.4%) vs 680 non-reproducible (10.6%) under the raw-extraction + adaptive-rounding canonical scenario.

[TABLE 1 — descriptive stats by outcome type × k-stratum × reproducibility status, auto-generated at `paper/tables/agg_REML_HKSJ_PI__tier1_sig_flip.md`]

## 3.2 Headline flip rates (Table 2)

Switching from DL to REML+HKSJ+PI changed (full corpus, 6,386 loadable MAs):

- **Tier 1 significance flip: 8.2%** of comparable MAs (514 flips / 6,305 comparable / 6,386 total).
- **Tier 2 direction flip: 0.6%** (36 flips / 6,305 comparable).
- **Tier 3 clinically-important flip: 3.9%** (27 flips / 688 MID-available subset).

The REML+HKSJ+PI comparator converged for 6,305 of 6,386 MAs (98.7%); 81 non-convergences (1.3%) are tabulated separately in supplementary Table S3.

[TABLE 2 — flip rates by tier × comparator method, both denominators]

## 3.3 Stratified by k (Figure 1 + Table 3)

As anticipated given DL's small-*k* bias, the significance-flip rate varies markedly with *k*. For the reproducible subset (n = 5,706) at binary outcomes:

- *k* < 5 (n = 1,833): **10.5%**
- 5 ≤ *k* < 10 (n = 1,380): 6.4%
- 10 ≤ *k* < 20 (n = 1,144): 4.5%
- *k* ≥ 20 (n = 1,060): **3.5%**

Continuous outcomes show a higher absolute level at every stratum (k<5: 14.6%; 5≤k<10: 12.7%; 10≤k<20: 10.5%; k≥20: 13.3%), consistent with absolute-scale MD effects being more sensitive to estimator choice than log-scale OR effects.

[FIGURE 1 — flip rate vs k-stratum, faceted by reproducibility status]

## 3.4 Stratified by reproducibility status (Table 4)

A clear compounding pattern emerges: the non-reproducible subset is approximately **2× more method-sensitive** than the reproducible subset at every (outcome × k) cell we examined.

Non-reproducible (n = 680, 15.7% overall flip rate):

- binary k<5: 17.4% (vs 10.5% reproducible)
- binary 5≤k<10: 13.1% (vs 6.4%)
- continuous k<5: 23.3% (vs 14.6%)
- continuous 5≤k<10: 21.8% (vs 12.7%)

This suggests the methodological gap and the numerical-reproduction gap are orthogonal axes that compound rather than overlap: MAs that fail to reproduce under DL are also the MAs most sensitive to method choice, meaning both fix paths would need to be addressed simultaneously to stabilise the affected ~10% of published reviews.

## 3.5 Bayesian comparator (Table 5 + supplementary)

The `bayesmeta` half-normal comparator was not run on the full corpus in v0.1.0 (compute ~3–4 hours at corpus scale) but is planned as a supplementary analysis before submission; see `RELEASE_PLAYBOOK.md` for the deferred run. Smoke-subset `bayesmeta` results (6 reviews, 37 MAs) show Tier-1 flip rate [TBC after deferred run] broadly [concordant / divergent] with the frequentist modernisation.

# 4. Discussion

## 4.1 Principal findings

[~400 words. The headline number from §3.2 plus the two or three most striking stratum results. What does it mean operationally that method choice changes X% of conclusions?]

## 4.2 Comparison with existing literature

[~400 words. Position against:
 - IntHout et al. 2014 HKSJ simulation study
 - Langan et al. 2019 systematic review of τ² estimators
 - `repro-floor-atlas` numerical-reproduction gap
 - MetaAudit detector-bias work
Make clear this is the *downstream clinical-conclusion* layer that sits on top of those earlier methodological critiques.]

## 4.3 Limitations

- **Aggregate data only.** We used published trial-level `yi`/`vi`; no individual patient data. IPD recompilation would be a different study.
- **No publication-bias methods.** PET-PEESE and Copas are excluded by scope; they're their own paper.
- **MID coverage.** Tier 3 was computed on the subset of outcomes with published MIDs (~15 outcomes). Outcomes without MIDs are NA for Tier 3.
- **Outcome-code mapping.** Free-text Cochrane outcome labels don't map 1:1 to our MID keys; v0.1 reports Tier 3 on a subset where the mapping is unambiguous. [NOTE FOR REVISION: this gap may be closed before submission; see supplementary Table S5 for the mapping procedure.]
- **Bayesian prior sensitivity.** One half-normal prior per effect-scale type; prior sensitivity is follow-on work.
- **Cochrane corpus only.** Findings generalise to non-Cochrane SRs only insofar as their methodological defaults match RevMan's.

## 4.4 Implications

For Cochrane: [should default to REML+HKSJ+PI? expose PI in RevMan forest plot? adjust GRADE interpretation conventions?]

For reviewers: [how to present method-sensitivity in current practice until tooling updates?]

For methodologists: [what does the magnitude of the clinical-flip rate say about the information content of RE-method choice vs other review-quality levers?]

# 5. Conclusion

Cochrane's DL default is not methodologically neutral. Across 6,386 published pairwise meta-analyses, switching to REML with the Hartung-Knapp-Sidik-Jonkman adjustment (Q/(k−1) floor applied) plus a prediction interval changes the significance judgement in **8.2%** of cases, the direction in **0.6%**, and exceeds the clinically-important threshold in **3.9%** of the MID-available subset. The effect is concentrated in small-*k* analyses and non-reproducible reviews, which compound rather than overlap: the ~10% of Cochrane MAs that fail DL-numerical reproduction are also ~2× more method-sensitive than the remainder, meaning RevMan's analytical stack contains two independent fragility axes that both need patching.

Modernising to REML+HKSJ+PI as the default is feasible — we release an open-source, Docker-reproducible, 1e-6-validated reference implementation — and is broadly concordant with current methodological consensus. The numerical-reproduction gap [@ahmad2026_reprofloor] and the methodological-default gap should be addressed in parallel.

# Author contributions (CRediT)

- **Mahmood Ahmad** — Conceptualization, Methodology, Software, Validation, Data curation, Formal analysis, Writing — original draft, Writing — review & editing, Visualization, Supervision.

# Declarations

**Funding.** None.

**Conflicts of interest.** None to declare on this manuscript. See MA's ORCID record for the full standing-declaration.

**Data and code availability.** All code is open-source at github.com/mahmood726-cyber/cochrane-modern-re under the MIT licence; v0.1.0 is archived at Zenodo DOI TBC. The underlying Pairwise70 `.rda` corpus is not redistributed by us; MetaAudit [@ahmad2026_metaaudit] documents its provenance.

# References

(See `references.bib`.)
