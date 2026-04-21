"""Preflight check: verify Pairwise70 corpus, MetaAudit, and repro-floor-atlas
reproducibility outputs are all locatable.

Fail-closed per rules.md. Exits non-zero with actionable remediation messages.

Env-driven path resolution (no hardcoded drives per Sentinel P0-hardcoded-local-path):
    PAIRWISE70_DIR  — Pairwise70 .rda corpus dir (expect ~1,000 .rda files)
    METAAUDIT_DIR   — MetaAudit `metaaudit/` package dir (contains loader.py)
    REPRO_FLOOR_ATLAS_DIR — repro-floor-atlas repo root (contains outputs/atlas.csv)

Sensible defaults for Mahmood's primary dev box are provided so zero-config
works there; anywhere else, set the env vars.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_DEFAULT_PAIRWISE70 = Path(r"C:\Projects\Pairwise70\data")
_DEFAULT_METAAUDIT = Path(r"C:\MetaAudit\metaaudit")
_DEFAULT_REPRO_FLOOR = Path(r"C:\Projects\repro-floor-atlas")

PAIRWISE70_DIR = Path(os.environ.get("PAIRWISE70_DIR", _DEFAULT_PAIRWISE70))
METAAUDIT_DIR = Path(os.environ.get("METAAUDIT_DIR", _DEFAULT_METAAUDIT))
REPRO_FLOOR_ATLAS_DIR = Path(os.environ.get("REPRO_FLOOR_ATLAS_DIR", _DEFAULT_REPRO_FLOOR))


def main() -> int:
    failures: list[str] = []

    if not PAIRWISE70_DIR.is_dir():
        failures.append(
            f"PAIRWISE70_DIR missing: {PAIRWISE70_DIR}. "
            f"Set env var PAIRWISE70_DIR to the Pairwise70 .rda corpus directory."
        )
    else:
        rda_files = list(PAIRWISE70_DIR.glob("*.rda"))
        if len(rda_files) < 100:
            failures.append(
                f"PAIRWISE70_DIR ({PAIRWISE70_DIR}) has only {len(rda_files)} .rda files; "
                f"expected ~1,000+. Wrong directory?"
            )

    if not METAAUDIT_DIR.is_dir():
        failures.append(
            f"METAAUDIT_DIR missing: {METAAUDIT_DIR}. "
            f"Set env var METAAUDIT_DIR to the metaaudit/ package directory."
        )
    else:
        required = ["__init__.py", "loader.py", "recompute.py"]
        missing = [f for f in required if not (METAAUDIT_DIR / f).exists()]
        if missing:
            failures.append(
                f"METAAUDIT_DIR ({METAAUDIT_DIR}) missing required files: {missing}"
            )

    atlas_csv = REPRO_FLOOR_ATLAS_DIR / "outputs" / "atlas.csv"
    if not atlas_csv.exists():
        failures.append(
            f"repro-floor-atlas atlas.csv missing at {atlas_csv}. "
            f"Set REPRO_FLOOR_ATLAS_DIR or run repro-floor-atlas scripts/run_atlas.py."
        )

    if failures:
        print("PREREQ FAIL:\n", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    rda_count = len(list(PAIRWISE70_DIR.glob("*.rda")))
    print(f"PREREQ OK")
    print(f"  PAIRWISE70_DIR = {PAIRWISE70_DIR}  ({rda_count} .rda files)")
    print(f"  METAAUDIT_DIR  = {METAAUDIT_DIR}")
    print(f"  atlas.csv      = {atlas_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
