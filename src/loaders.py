"""Pairwise70 → MA iterator.

Loads .rda files from PAIRWISE70_DIR via MetaAudit's loader, computes per-study
yi/vi via MetaAudit's recompute functions, and merges reproducibility status
from repro-floor-atlas outputs/atlas.csv.

Effect-measure conventions at v0.1 (fixed; not per-MA configurable):
    binary      → logOR via compute_log_or (cc=0.5 if any zero cell)
    continuous  → MD via compute_md
    GIV         → passthrough (vi = se^2)

Outcome-code mapping: .rda files carry free-text outcome labels that don't
map 1:1 to MID lookup keys. v0.1 defaults outcome_code to "unknown_outcome"
and tier3_mid_flip will be NA corpus-wide. Building the mapping layer is
follow-on work (see MID lookup table in data/mid_lookup.yaml for keys).
"""
from __future__ import annotations

import logging
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from src.ma_types import MA, EffectScale, OutcomeType, ReproStatus, Study
from src.outcome_mapper import map_outcome

logger = logging.getLogger(__name__)

try:
    from src.paths_local import (
        DEFAULT_METAAUDIT as _DEFAULT_METAAUDIT,
        DEFAULT_PAIRWISE70 as _DEFAULT_PAIRWISE70,
        DEFAULT_REPRO_FLOOR as _DEFAULT_REPRO_FLOOR,
    )
except ImportError:
    _DEFAULT_PAIRWISE70 = _DEFAULT_METAAUDIT = _DEFAULT_REPRO_FLOOR = None  # type: ignore[assignment]


class LoaderError(Exception):
    """Raised on data integrity errors that must halt the pipeline."""


def _resolve_path(env_var: str, fallback: Path | None) -> Path | None:
    """Env var wins; paths_local fallback only used if env not set."""
    val = os.environ.get(env_var)
    if val:
        return Path(val)
    return fallback


def _auto_setup_metaaudit() -> None:
    """Insert METAAUDIT_DIR's parent on sys.path at import time if locatable.

    Silent no-op if not locatable — call sites raise LoaderError with a
    helpful message if metaaudit is actually needed and missing.
    """
    candidate = _resolve_path("METAAUDIT_DIR", _DEFAULT_METAAUDIT)
    if candidate is not None and candidate.is_dir():
        parent = str(candidate.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)


_auto_setup_metaaudit()


def _ensure_metaaudit_on_path(metaaudit_dir: Path) -> None:
    if not metaaudit_dir.is_dir():
        raise LoaderError(
            f"METAAUDIT_DIR not found: {metaaudit_dir}. "
            "Set env var METAAUDIT_DIR or install MetaAudit at the default location."
        )
    parent = str(metaaudit_dir.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)


@dataclass(frozen=True)
class LoadResult:
    mas: list[MA]
    skip_log: dict[str, str]


def load_reproducibility_status(atlas_csv: Path) -> dict[str, ReproStatus]:
    """Parse atlas.csv and return {ma_id → reproducibility_status}.

    We use the `raw_extraction` + `adaptive` row as the canonical verdict
    (matches repro-floor-atlas README §Methods).
    """
    if not atlas_csv.exists():
        logger.warning("atlas.csv not at %s; reproducibility_status will be 'unknown'", atlas_csv)
        return {}
    df = pd.read_csv(atlas_csv)
    canonical = df[
        (df["scenario"] == "raw_extraction") & (df["rounding_mode"] == "adaptive")
    ]
    mapping: dict[str, ReproStatus] = {}
    for ma_id, g in canonical.groupby("ma_id"):
        exceeded = bool(g["exceeds_fixed"].any() or g["exceeds_adaptive"].any())
        mapping[str(ma_id)] = "non_reproducible" if exceeded else "reproducible"
    return mapping


def _effect_scale_for(data_type: str) -> EffectScale:
    """v0.1 fixed mapping: binary→logOR, continuous→MD, giv→GIV."""
    if data_type == "binary":
        return "logOR"
    if data_type == "continuous":
        return "MD"
    if data_type == "giv":
        return "GIV"
    raise LoaderError(f"unknown data_type: {data_type!r}")


def _outcome_type_for(data_type: str) -> OutcomeType:
    if data_type == "binary":
        return "binary"
    if data_type == "continuous":
        return "continuous"
    if data_type == "giv":
        return "GIV"
    raise LoaderError(f"unknown data_type: {data_type!r}")


def _studies_from_inputs(ma_inputs) -> list[Study] | None:
    """Return list[Study] or None if computation fails / too few valid studies."""
    from metaaudit.recompute import compute_log_or, compute_md

    if ma_inputs.data_type == "binary" and ma_inputs.binary is not None:
        b = ma_inputs.binary
        yi, vi = compute_log_or(b.e_cases, b.e_n, b.c_cases, b.c_n)
    elif ma_inputs.data_type == "continuous" and ma_inputs.continuous is not None:
        c = ma_inputs.continuous
        yi, vi = compute_md(c.e_mean, c.e_sd, c.e_n, c.c_mean, c.c_sd, c.c_n)
    elif ma_inputs.data_type == "giv" and ma_inputs.giv is not None:
        g = ma_inputs.giv
        yi = g.yi
        vi = g.se ** 2
    else:
        return None

    valid = ~(np.isnan(yi) | np.isnan(vi) | (vi <= 0))
    yi = yi[valid]
    vi = vi[valid]
    if len(yi) < 2:
        return None
    return [Study(yi=float(y), vi=float(v)) for y, v in zip(yi, vi)]


def iter_mas_with_log(
    *,
    pairwise70_dir: Path | None = None,
    metaaudit_dir: Path | None = None,
    atlas_csv: Path | None = None,
    max_reviews: int | None = None,
) -> LoadResult:
    """Load all MAs from the Pairwise70 corpus.

    Returns: LoadResult with `mas` (usable) and `skip_log` (ma_id → reason_code).
    """
    pairwise70_dir = pairwise70_dir or _resolve_path("PAIRWISE70_DIR", _DEFAULT_PAIRWISE70)
    metaaudit_dir = metaaudit_dir or _resolve_path("METAAUDIT_DIR", _DEFAULT_METAAUDIT)
    repro_floor_dir = _resolve_path("REPRO_FLOOR_ATLAS_DIR", _DEFAULT_REPRO_FLOOR)
    atlas_csv = atlas_csv or (repro_floor_dir / "outputs" / "atlas.csv" if repro_floor_dir else None)

    if pairwise70_dir is None:
        raise LoaderError(
            "PAIRWISE70_DIR not set and no paths_local.py fallback found. "
            "Set env var or copy src/paths_local.example.py to src/paths_local.py."
        )
    if metaaudit_dir is None:
        raise LoaderError(
            "METAAUDIT_DIR not set and no paths_local.py fallback found."
        )

    _ensure_metaaudit_on_path(metaaudit_dir)
    from metaaudit.loader import load_all_reviews  # noqa: E402

    repro_status = load_reproducibility_status(atlas_csv)
    reviews = load_all_reviews(pairwise70_dir, max_reviews=max_reviews)

    mas: list[MA] = []
    skip_log: dict[str, str] = {}
    seen_ids: set[str] = set()

    for review in reviews:
        for ag in review.analyses:
            ma_id = str(ag.ma_id)
            if ma_id in seen_ids:
                raise LoaderError(
                    f"dataset_integrity_error: duplicate ma_id '{ma_id}' in {pairwise70_dir}"
                )
            seen_ids.add(ma_id)

            # Inline the per-analysis conversion (bypasses repro-floor-atlas
            # which has its own loader but pulls in unrelated deps).
            try:
                data_type = ag.data_type.value  # "binary" | "continuous" | "giv"
            except AttributeError:
                data_type = str(ag.data_type).lower().replace("datatype.", "")

            # Build a minimal MAInputs-equivalent from the AnalysisGroup
            from dataclasses import dataclass as _dc

            @_dc(frozen=True)
            class _Inputs:
                data_type: str
                binary: object = None
                continuous: object = None
                giv: object = None

            binary = continuous = giv = None
            df = ag.df
            if data_type == "binary":
                from metaaudit.loader import BINARY_COLS
                if not all(c in df.columns for c in BINARY_COLS):
                    skip_log[ma_id] = "insufficient_data"
                    continue
                from types import SimpleNamespace
                binary = SimpleNamespace(
                    e_cases=df["Experimental.cases"].to_numpy(dtype=float),
                    e_n=df["Experimental.N"].to_numpy(dtype=float),
                    c_cases=df["Control.cases"].to_numpy(dtype=float),
                    c_n=df["Control.N"].to_numpy(dtype=float),
                )
            elif data_type == "continuous":
                from metaaudit.loader import CONTINUOUS_COLS
                if not all(c in df.columns for c in CONTINUOUS_COLS):
                    skip_log[ma_id] = "insufficient_data"
                    continue
                from types import SimpleNamespace
                continuous = SimpleNamespace(
                    e_mean=df["Experimental.mean"].to_numpy(dtype=float),
                    e_sd=df["Experimental.SD"].to_numpy(dtype=float),
                    e_n=df["Experimental.N"].to_numpy(dtype=float),
                    c_mean=df["Control.mean"].to_numpy(dtype=float),
                    c_sd=df["Control.SD"].to_numpy(dtype=float),
                    c_n=df["Control.N"].to_numpy(dtype=float),
                )
            elif data_type == "giv":
                from metaaudit.loader import GIV_COLS
                if not all(c in df.columns for c in GIV_COLS):
                    skip_log[ma_id] = "insufficient_data"
                    continue
                from types import SimpleNamespace
                giv = SimpleNamespace(
                    yi=df["GIV.Mean"].to_numpy(dtype=float),
                    se=df["GIV.SE"].to_numpy(dtype=float),
                )
            else:
                skip_log[ma_id] = "insufficient_data"
                continue

            inputs = _Inputs(data_type=data_type, binary=binary,
                             continuous=continuous, giv=giv)
            studies = _studies_from_inputs(inputs)
            if studies is None:
                skip_log[ma_id] = "insufficient_data"
                continue

            # Heuristic outcome-code mapping from Analysis.name free text.
            analysis_name = None
            if "Analysis.name" in df.columns and len(df) > 0:
                analysis_name = str(df["Analysis.name"].iloc[0])  # type: ignore[index]

            mas.append(MA(
                ma_id=ma_id,
                review_id=str(ag.review_id),
                outcome_type=_outcome_type_for(data_type),
                outcome_code=map_outcome(analysis_name),
                effect_scale=_effect_scale_for(data_type),
                studies=tuple(studies),
                k=len(studies),
                reproducibility_status=repro_status.get(ma_id, "unknown"),
            ))

    logger.info(
        "loaded %d MAs (%d skipped) from %s",
        len(mas), len(skip_log), pairwise70_dir,
    )
    return LoadResult(mas=mas, skip_log=skip_log)


def iter_mas(**kwargs) -> Iterator[MA]:
    """Convenience wrapper that yields MAs and discards the skip_log.

    Use iter_mas_with_log() when you need the reason codes.
    """
    result = iter_mas_with_log(**kwargs)
    yield from result.mas
