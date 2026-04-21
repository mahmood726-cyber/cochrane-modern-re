"""Python façade over R method runners.

Batches by (effect_scale × method) and calls `Rscript run_metafor.R` or
`Rscript run_bayesmeta.R` with JSON over stdio. Returns MethodResult objects.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from src.ma_types import MA, MethodResult

logger = logging.getLogger(__name__)

SRC_DIR = Path(__file__).resolve().parent
R_SCRIPTS = SRC_DIR / "r_scripts"
BATCH_TIMEOUT_SEC = 600  # 10 min per batch hard cap

DeterministicMethod = Literal["DL", "REML_only", "REML_HKSJ_PI"]


def _find_rscript() -> str:
    rscript = shutil.which("Rscript")
    if rscript:
        return rscript
    fallback = r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe"
    if Path(fallback).exists():
        return fallback
    raise RuntimeError("Rscript not found on PATH or at default Windows path")


def _call_r(script: Path, payload: dict) -> list[dict]:
    proc = subprocess.run(
        [_find_rscript(), str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=BATCH_TIMEOUT_SEC,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"R subprocess failed (exit={proc.returncode}): {proc.stderr[-2000:]}"
        )
    # R may emit warning messages on stderr; they're not fatal. Parse stdout.
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"R subprocess produced non-JSON stdout: {proc.stdout[:500]!r} "
            f"(stderr={proc.stderr[:500]!r})"
        ) from e


def _batch_payload(mas: Sequence[MA]) -> list[dict]:
    return [
        {
            "ma_id": m.ma_id,
            "yi": [float(s.yi) for s in m.studies],
            "vi": [float(s.vi) for s in m.studies],
        }
        for m in mas
    ]


def run_batch(
    *,
    method: DeterministicMethod,
    effect_scale: str,
    mas: Sequence[MA],
) -> list[MethodResult]:
    """Run one deterministic method (DL / REML_only / REML_HKSJ_PI) on a batch.

    All MAs must share the same effect_scale (caller groups them).
    """
    if not mas:
        return []
    payload = {
        "method": method,
        "effect_scale": effect_scale,
        "batch": _batch_payload(mas),
    }
    raw = _call_r(R_SCRIPTS / "run_metafor.R", payload)
    return [_to_metafor_result(r, method) for r in raw]


def _to_metafor_result(raw: dict, method: DeterministicMethod) -> MethodResult:
    return MethodResult(
        ma_id=raw["ma_id"],
        method=method,
        estimate=raw.get("estimate"),
        se=raw.get("se"),
        ci_lo=raw.get("ci_lo"),
        ci_hi=raw.get("ci_hi"),
        tau2=raw.get("tau2"),
        i2=raw.get("i2"),
        pi_lo=raw.get("pi_lo"),
        pi_hi=raw.get("pi_hi"),
        k_effective=int(raw["k_effective"]),
        converged=bool(raw["converged"]),
        rhat=None,
        ess=None,
        reason_code=raw.get("reason_code", ""),
    )
