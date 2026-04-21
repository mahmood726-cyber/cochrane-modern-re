"""Local path overrides — copy this file to `paths_local.py` and edit.

`paths_local.py` is gitignored (not committed) so your local machine's
absolute paths never leak into the repo. Source code imports lazily:

    try:
        from src.paths_local import DEFAULT_PAIRWISE70, DEFAULT_METAAUDIT, DEFAULT_REPRO_FLOOR
    except ImportError:
        DEFAULT_PAIRWISE70 = DEFAULT_METAAUDIT = DEFAULT_REPRO_FLOOR = None

If `paths_local.py` is absent AND no env vars are set, loaders/validation
fail closed with a remediation message pointing at `scripts/prereq_check.py`.

Env vars always override `paths_local.py` values when both exist.
"""
from __future__ import annotations

from pathlib import Path

# Edit these to point at your local data/code locations.
DEFAULT_PAIRWISE70: Path | None = Path(r"/path/to/Pairwise70/data")
DEFAULT_METAAUDIT: Path | None = Path(r"/path/to/MetaAudit/metaaudit")
DEFAULT_REPRO_FLOOR: Path | None = Path(r"/path/to/repro-floor-atlas")
