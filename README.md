# cochrane-modern-re

Reference implementation + demonstrator paper: four random-effects methods (DerSimonian-Laird baseline, REML-only ablation, REML+HKSJ+PI, Bayesian half-normal via `bayesmeta`) applied to the 7,545 Cochrane pairwise meta-analyses in the Pairwise70 corpus. Target journal: Research Synthesis Methods.

## Status

v0.1.0-dev. Not yet usable — implementation in progress on `feat/v0.1-implementation`. See `docs/superpowers/plans/2026-04-21-cochrane-modern-re.md` for the task breakdown.

## Reproduce

Full reproducibility is a v0.1.0 release goal. Once tagged:

```bash
docker build -t cochrane-modern-re .
docker run --rm -v $(pwd):/work cochrane-modern-re bash -c "cd /work && python -m pytest"
```

## Documents

- Spec: `docs/superpowers/specs/2026-04-21-cochrane-modern-re-design.md`
- Implementation plan: `docs/superpowers/plans/2026-04-21-cochrane-modern-re.md`
- Sibling project: [repro-floor-atlas](https://github.com/mahmood726-cyber/repro-floor-atlas) (provides the Pairwise70 cache; post-publication, this repo merges into `repro-floor-atlas/modern_re/` for v0.2.0).

## Licence

TBD (likely MIT at v0.1.0 release).
