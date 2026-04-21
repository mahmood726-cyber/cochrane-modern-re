"""Preflight check: verify Pairwise70 corpus, MetaAudit, and repro-floor-atlas
reproducibility outputs are all locatable.

Fail-closed per rules.md. Exits non-zero with actionable remediation messages.

Path resolution order:
    1. Env var (PAIRWISE70_DIR / METAAUDIT_DIR / REPRO_FLOOR_ATLAS_DIR)
    2. src/paths_local.py (gitignored; copy from paths_local.example.py)
    3. Fail closed with remediation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from src.paths_local import (
        DEFAULT_METAAUDIT as _DEFAULT_METAAUDIT,
        DEFAULT_PAIRWISE70 as _DEFAULT_PAIRWISE70,
        DEFAULT_REPRO_FLOOR as _DEFAULT_REPRO_FLOOR,
    )
except ImportError:
    _DEFAULT_PAIRWISE70 = _DEFAULT_METAAUDIT = _DEFAULT_REPRO_FLOOR = None  # type: ignore[assignment]


def _resolve(env_var: str, fallback: Path | None) -> Path | None:
    val = os.environ.get(env_var)
    if val:
        return Path(val)
    return fallback


def main() -> int:
    pairwise70_dir = _resolve("PAIRWISE70_DIR", _DEFAULT_PAIRWISE70)
    metaaudit_dir = _resolve("METAAUDIT_DIR", _DEFAULT_METAAUDIT)
    repro_floor_dir = _resolve("REPRO_FLOOR_ATLAS_DIR", _DEFAULT_REPRO_FLOOR)

    failures: list[str] = []

    if pairwise70_dir is None:
        failures.append(
            "PAIRWISE70_DIR not set. Set env var or copy "
            "src/paths_local.example.py to src/paths_local.py and edit."
        )
    elif not pairwise70_dir.is_dir():
        failures.append(f"PAIRWISE70_DIR does not resolve to a directory: {pairwise70_dir}")
    else:
        rda_files = list(pairwise70_dir.glob("*.rda"))
        if len(rda_files) < 100:
            failures.append(
                f"PAIRWISE70_DIR has only {len(rda_files)} .rda files; expected ~1,000+."
            )

    if metaaudit_dir is None:
        failures.append("METAAUDIT_DIR not set.")
    elif not metaaudit_dir.is_dir():
        failures.append(f"METAAUDIT_DIR does not resolve: {metaaudit_dir}")
    else:
        required = ["__init__.py", "loader.py", "recompute.py"]
        missing = [f for f in required if not (metaaudit_dir / f).exists()]
        if missing:
            failures.append(f"METAAUDIT_DIR missing required files: {missing}")

    atlas_csv = (repro_floor_dir / "outputs" / "atlas.csv") if repro_floor_dir else None
    if atlas_csv is None:
        failures.append("REPRO_FLOOR_ATLAS_DIR not set.")
    elif not atlas_csv.exists():
        failures.append(f"atlas.csv missing: {atlas_csv}")

    if failures:
        print("PREREQ FAIL:\n", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    rda_count = len(list(pairwise70_dir.glob("*.rda")))
    print("PREREQ OK")
    print(f"  PAIRWISE70_DIR  has {rda_count} .rda files")
    print(f"  METAAUDIT_DIR   present with loader.py")
    print(f"  atlas.csv       present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
