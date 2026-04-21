# data/

## External data sources (not committed)

This project consumes three external data sources. None are redistributed in this repo.

### 1. Pairwise70 `.rda` corpus

- **What:** Study-level Cochrane meta-analysis data. 1,096 `.rda` files covering 7,545 meta-analyses across 595 reviews.
- **How to access:** Set `PAIRWISE70_DIR` env var (or use the default `C:\Projects\Pairwise70\data` on Mahmood's dev box).
- **Format:** R `.rda` files per review, each containing one or more `AnalysisGroup` DataFrames with per-study columns like `Experimental.cases`, `Experimental.N`, `Control.cases`, `Control.N` (binary); `Experimental.mean`, `Experimental.SD`, `Experimental.N`, `Control.mean`, `Control.SD`, `Control.N` (continuous); `GIV.Mean`, `GIV.SE` (generic inverse variance).
- **Access pattern:** via `metaaudit.loader.load_all_reviews()`.

### 2. MetaAudit package

- **What:** Python package providing the `.rda` loader and re-compute logic.
- **How to access:** Set `METAAUDIT_DIR` env var to the `metaaudit/` package directory (the one containing `__init__.py`, `loader.py`, `recompute.py`).
- **Default:** `C:\MetaAudit\metaaudit`.
- **Note:** MetaAudit lacks PyPI packaging; loaded via sys.path insertion (see `src/loaders.py`).

### 3. repro-floor-atlas output

- **What:** Per-MA reproducibility status (reproducible vs non-reproducible at |Δ|>0.005 under RevMan DL replay).
- **How to access:** `REPRO_FLOOR_ATLAS_DIR/outputs/atlas.csv` (60k-row CSV; each MA has multiple rows for different rounding scenarios — we use `scenario="raw_extraction"` + `rounding_mode="adaptive"` as canonical).
- **Default:** `C:\Projects\repro-floor-atlas`.

## Committed files

- `mid_lookup.yaml` — MID (Minimal Important Difference) table for Tier 3 flip classification. Small, hand-curated, extensible.

## Deviation from v0.1 spec

The v0.1 spec (`docs/superpowers/specs/2026-04-21-cochrane-modern-re-design.md`) assumed a pre-built `pairwise70_cache/` directory. Investigation at Task 0.3 found that no such cache exists — `repro-floor-atlas` accesses `.rda` files directly via MetaAudit's loader. This project adopts the same pattern. Spec §4.1 and plan §2 loader task should be read as "loads via MetaAudit from `PAIRWISE70_DIR`" rather than "reads pairwise70_cache parquet".

## Running the prereq check

```bash
python scripts/prereq_check.py
```

Expected output when all three sources are wired:

```
PREREQ OK
  PAIRWISE70_DIR = C:\Projects\Pairwise70\data  (1096 .rda files)
  METAAUDIT_DIR  = C:\MetaAudit\metaaudit
  atlas.csv      = C:\Projects\repro-floor-atlas\outputs\atlas.csv
```
