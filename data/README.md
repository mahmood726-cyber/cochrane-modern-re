# data/

## External data sources (not committed)

This project consumes three external data sources. None are redistributed in this repo.

### 1. Pairwise70 `.rda` corpus

- **What:** Study-level Cochrane meta-analysis data. ~1,000 `.rda` files covering 7,545 meta-analyses across 595 reviews.
- **How to access:** Set `PAIRWISE70_DIR` env var, OR copy `src/paths_local.example.py` to `src/paths_local.py` and edit in your local path.
- **Format:** R `.rda` files per review. Each contains one or more `AnalysisGroup` DataFrames with per-study columns:
  - binary: `Experimental.cases`, `Experimental.N`, `Control.cases`, `Control.N`
  - continuous: `Experimental.mean`, `Experimental.SD`, `Experimental.N`, `Control.mean`, `Control.SD`, `Control.N`
  - GIV: `GIV.Mean`, `GIV.SE`
- **Access pattern:** via `metaaudit.loader.load_all_reviews()`.

### 2. MetaAudit package

- **What:** Python package providing the `.rda` loader and recompute logic.
- **How to access:** Set `METAAUDIT_DIR` env var, OR edit `src/paths_local.py`.
- **Note:** MetaAudit lacks PyPI packaging; loaded via sys.path insertion (see `src/loaders.py`).

### 3. repro-floor-atlas output

- **What:** Per-MA reproducibility status (reproducible vs non-reproducible at |Δ|>0.005 under RevMan DL replay).
- **How to access:** Set `REPRO_FLOOR_ATLAS_DIR` env var, OR edit `src/paths_local.py`. Loader reads `$REPRO_FLOOR_ATLAS_DIR/outputs/atlas.csv`.

## Committed files

- `mid_lookup.yaml` — MID (Minimal Important Difference) table for Tier 3 flip classification. 15 outcomes + SMD fallback.

## Path resolution

1. Env var wins if set.
2. Otherwise `src/paths_local.py` (gitignored) is consulted.
3. Otherwise fail closed with remediation message.

Run `python scripts/prereq_check.py` to verify.

## Deviation from v0.1 spec

The v0.1 spec (`docs/superpowers/specs/2026-04-21-cochrane-modern-re-design.md`) assumed a pre-built `pairwise70_cache/` directory. Investigation at Task 0.3 found that no such cache exists — `repro-floor-atlas` accesses `.rda` files directly via MetaAudit's loader. This project adopts the same pattern. Spec §4.1 and plan §2 loader task should be read as "loads via MetaAudit from `PAIRWISE70_DIR`" rather than "reads pairwise70_cache parquet".
