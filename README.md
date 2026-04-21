# cochrane-modern-re

Reference implementation + demonstrator paper: four random-effects methods — **DerSimonian-Laird** (RevMan baseline), **REML-only** (ablation), **REML+HKSJ+PI** (modern frequentist), and **`bayesmeta`** half-normal (Bayesian) — applied to the 7,545 pairwise Cochrane meta-analyses in the Pairwise70 corpus. Paper target: *Research Synthesis Methods*.

## Status

**v0.1.0-dev** on branch `feat/v0.1-implementation`. Not yet released. Analytical pipeline complete; full-corpus run in progress.

### Full-corpus results (DL → REML+HKSJ+PI, 6,386 MAs from 582 Cochrane reviews)

| Tier | Rate | n |
|---|---|---|
| 1 — Significance flip | **8.2%** | 514 / 6,305 comparable |
| 2 — Direction flip | 0.6% | 36 / 6,305 |
| 3 — Clinically-important flip (MID-available subset) | 3.9% | 27 / 688 |

### Non-reproducible subset (680 MAs) — 2× more method-sensitive

| Tier | Rate | n |
|---|---|---|
| 1 — Significance flip | **15.7%** | 106 / 675 comparable |
| 2 — Direction flip | 1.3% | 9 / 675 |
| 3 — Clinically-important flip | 1.6% | 1 / 61 |

Clean stratum gradient (supports DL small-k bias theory):

| Stratum | n | Tier-1 flip rate |
|---|---|---|
| continuous, k<5 | 163 | 23.3% |
| continuous, 5≤k<10 | 110 | 21.8% |
| binary, k<5 | 86 | 17.4% |
| continuous, 10≤k<20 | 72 | 16.7% |
| binary, 5≤k<10 | 61 | 13.1% |
| binary, 10≤k<20 | 43 | 7.0% |
| binary, k≥20 | 57 | 1.8% |

## Reproduce

Prereqs: Python ≥ 3.11, R 4.5.2, access to the Pairwise70 corpus (via [MetaAudit](https://github.com/mahmood726-cyber/MetaAudit)) and the [repro-floor-atlas](https://github.com/mahmood726-cyber/repro-floor-atlas) output.

```bash
# Copy the template and edit your local paths
cp src/paths_local.example.py src/paths_local.py
# edit to point at your Pairwise70 / MetaAudit / repro-floor-atlas

# Verify environment
python scripts/prereq_check.py

# Install
pip install -e ".[dev]"
Rscript install_r_deps.R

# Test (should report 92 passed)
python -m pytest

# Run the non-reproducible subset (fast — ~20 min without bayesmeta)
python analysis/01_run_methods.py --subset non_reproducible --skip-bayes --out outputs/nr_method_results.parquet
python analysis/02_classify_flips.py --method-results outputs/nr_method_results.parquet --out outputs/nr_flips.parquet
python analysis/03_aggregate.py --flips outputs/nr_flips.parquet --out-dir outputs/nr --tables-dir paper/tables/non_reproducible
python analysis/04_build_dashboard.py --agg-dir outputs/nr --out docs/non_reproducible_index.html --version 0.1.0-nr

# Validate against independent metafor reference at 1e-6
python -m src.validation
```

Docker (when v0.1.0 is tagged):
```bash
docker build -t cochrane-modern-re .
docker run --rm -v $(pwd):/work cochrane-modern-re python -m pytest
```

## Documents

- **Spec:** `docs/superpowers/specs/2026-04-21-cochrane-modern-re-design.md`
- **Implementation plan:** `docs/superpowers/plans/2026-04-21-cochrane-modern-re.md`
- **Paper skeleton:** `paper/manuscript.md`
- **Changelog:** `CHANGELOG.md`

## Methods overview

### HKSJ Q/(k−1) floor

`metafor::rma(..., test="knha")` applies the Hartung-Knapp-Sidik-Jonkman adjustment directly without the [IntHout et al. 2014](https://doi.org/10.1186/1471-2288-14-25) Q/(k−1) floor. Without the floor, HKSJ can spuriously *narrow* the CI below the REML+Wald reference when studies are near-homogeneous. We enforce the floor in `src/r_scripts/run_metafor.R` by comparing the HKSJ SE against the REML+Wald SE and taking the larger, then reconstructing the CI with the *t*_{k−1} critical value.

### Tier 3 — scale-aware MID flip

For ratio outcomes (logRR/logOR/logHR) the MID comparison is on the natural scale after back-transform: `|exp(est_baseline) − exp(est_comparator)| > MID`. For continuous outcomes (SMD/MD/GIV) the comparison is direct. MID values in `data/mid_lookup.yaml` specify `{mid, scale, source}`.

### Independent validation

`src/validation.py` + `scripts/validation_reference.R` run DL and REML-only through a second, deliberately-differently-written path and assert 1e-6 agreement with the main wrapper. HKSJ is excluded because our wrapper floors while raw metafor doesn't; HKSJ correctness is validated behaviourally in `tests/test_methods.py::test_hksj_floor_prevents_narrowing_below_dl`.

## Related projects

- [`repro-floor-atlas`](https://github.com/mahmood726-cyber/repro-floor-atlas) — numerical reproduction-floor primitive providing the `atlas.csv` input used here.
- [`MetaAudit`](https://github.com/mahmood726-cyber/MetaAudit) — `.rda` loader + eleven pre-specified detectors for meta-analysis integrity.

After v0.1.0 publication, this project will be folded into `repro-floor-atlas/modern_re/` as part of repro-floor-atlas v0.2.0. The Zenodo-archived tag remains the canonical citation.

## Licence

MIT — see `LICENSE`.

## Citation

Once v0.1.0 is released, cite as:

> Ahmad M. (2026). cochrane-modern-re v0.1.0. Zenodo. [DOI TBC]

And the companion paper when accepted:

> Ahmad M. (2026). Modern random-effects methods change clinical conclusions in X% of Cochrane pairwise meta-analyses. *Research Synthesis Methods*. [DOI TBC]
