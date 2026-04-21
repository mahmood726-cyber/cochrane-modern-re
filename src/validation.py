"""Numerical validation harness — compare main wrapper against raw metafor.

Runs DL and REML_only through both paths:
  - Main wrapper: src/methods.run_batch() → src/r_scripts/run_metafor.R
  - Independent reference: scripts/validation_reference.R (raw metafor, no floor)

Asserts agreement within 1e-6 on (estimate, SE, tau²) for every MA where both
sides converge. HKSJ is excluded from this harness because the wrapper applies
the Q/(k-1) floor documented in advanced-stats.md; HKSJ behavior is validated
behaviourally in tests/test_methods.py.

Release-gate: CI release tier calls this on the full corpus. Any drift blocks
the release.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import click
import pandas as pd

from src.loaders import iter_mas_with_log
from src.methods import run_batch

logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent
REFERENCE_SCRIPT = REPO / "scripts" / "validation_reference.R"
TOLERANCE = 1e-6


@dataclass
class DriftRow:
    ma_id: str
    method: str
    field: str
    wrapper: float
    reference: float
    diff: float


def _find_rscript() -> str:
    rscript = shutil.which("Rscript")
    if rscript:
        return rscript
    fallback = r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe"
    if Path(fallback).exists():
        return fallback
    raise RuntimeError("Rscript not found")


def _call_reference(payload: dict, timeout: int) -> list[dict]:
    proc = subprocess.run(
        [_find_rscript(), str(REFERENCE_SCRIPT)],
        input=json.dumps(payload), capture_output=True, text=True,
        encoding="utf-8", timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"reference script failed: {proc.stderr[-2000:]}")
    return json.loads(proc.stdout)


def validate(
    *,
    max_reviews: int | None = None,
    tolerance: float = TOLERANCE,
    timeout: int = 1800,
) -> list[DriftRow]:
    """Run both paths on the (subset of the) corpus and return any drift rows.

    Empty return = clean validation.
    """
    mas = iter_mas_with_log(max_reviews=max_reviews).mas
    logger.info("validating %d MAs at tolerance=%g", len(mas), tolerance)

    # Main wrapper outputs
    wrapper_out: dict[tuple[str, str], dict] = {}
    for scale in {m.effect_scale for m in mas}:
        group = [m for m in mas if m.effect_scale == scale]
        for method in ("DL", "REML_only"):
            for r in run_batch(method=method, effect_scale=scale, mas=group):
                wrapper_out[(r.ma_id, method)] = {
                    "estimate": r.estimate, "se": r.se,
                    "tau2": r.tau2 if method == "REML_only" else None,
                }

    # Independent reference (one batch)
    payload = {
        "batch": [
            {"ma_id": m.ma_id, "yi": [s.yi for s in m.studies], "vi": [s.vi for s in m.studies]}
            for m in mas
        ],
    }
    reference_list = _call_reference(payload, timeout=timeout)
    reference_by_id = {r["ma_id"]: r for r in reference_list}

    drifts: list[DriftRow] = []
    for m in mas:
        ref = reference_by_id.get(m.ma_id)
        if not ref:
            continue
        checks = [
            ("DL", "estimate", wrapper_out.get((m.ma_id, "DL"), {}).get("estimate"), ref.get("dl_est")),
            ("DL", "se", wrapper_out.get((m.ma_id, "DL"), {}).get("se"), ref.get("dl_se")),
            ("REML_only", "estimate", wrapper_out.get((m.ma_id, "REML_only"), {}).get("estimate"), ref.get("reml_est")),
            ("REML_only", "se", wrapper_out.get((m.ma_id, "REML_only"), {}).get("se"), ref.get("reml_se")),
            ("REML_only", "tau2", wrapper_out.get((m.ma_id, "REML_only"), {}).get("tau2"), ref.get("reml_tau2")),
        ]
        for method, field, w, r in checks:
            if w is None or r is None:
                continue
            diff = abs(w - r)
            if diff > tolerance:
                drifts.append(DriftRow(
                    ma_id=m.ma_id, method=method, field=field,
                    wrapper=w, reference=r, diff=diff,
                ))
    return drifts


@click.command()
@click.option("--max-reviews", type=int, default=None,
              help="Limit to first N reviews (for dev / smoke)")
@click.option("--tolerance", type=float, default=TOLERANCE)
@click.option("--out", type=click.Path(path_type=Path),
              default=Path("outputs/validation_drift.csv"))
def main(max_reviews: int | None, tolerance: float, out: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    drifts = validate(max_reviews=max_reviews, tolerance=tolerance)
    if drifts:
        df = pd.DataFrame([d.__dict__ for d in drifts])
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        print(f"DRIFT detected in {len(drifts)} (ma_id, method, field) triples", file=sys.stderr)
        print(f"  see {out}", file=sys.stderr)
        raise SystemExit(1)
    print("validation: clean")


if __name__ == "__main__":
    main()
