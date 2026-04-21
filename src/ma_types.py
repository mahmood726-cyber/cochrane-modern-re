"""Dataclasses pinning the inter-module contracts.

Every field name here is part of the public contract between modules. Renaming
any of these breaks the contract tests intentionally — that's the point.
See `lessons.md` — "Integration Contracts: field-name contract tests between
modules" — for the incident this defends against (MetaReproducer P0-1).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EffectScale = Literal["logRR", "logOR", "logHR", "SMD", "MD", "GIV"]
OutcomeType = Literal["binary", "continuous", "GIV"]
ReproStatus = Literal["reproducible", "non_reproducible", "unknown"]
MethodName = Literal["DL", "REML_only", "REML_HKSJ_PI", "bayesmeta_HN"]
ReasonCode = Literal[
    "",
    "insufficient_data",
    "invalid_variance",
    "dataset_integrity_error",
    "k_too_small",
    "pi_undefined_k_lt_3",
    "r_subprocess_error",
    "bayes_unconverged",
    "comparison_unavailable",
    "comparator_unconverged",
]


@dataclass(frozen=True)
class Study:
    yi: float
    vi: float


@dataclass(frozen=True)
class MA:
    ma_id: str
    review_id: str
    outcome_type: OutcomeType
    outcome_code: str
    effect_scale: EffectScale
    studies: tuple[Study, ...]
    k: int
    reproducibility_status: ReproStatus


@dataclass(frozen=True)
class MethodResult:
    ma_id: str
    method: MethodName
    estimate: float | None
    se: float | None
    ci_lo: float | None
    ci_hi: float | None
    tau2: float | None
    i2: float | None
    pi_lo: float | None
    pi_hi: float | None
    k_effective: int
    converged: bool
    rhat: float | None
    ess: float | None
    reason_code: ReasonCode


@dataclass(frozen=True)
class FlipResult:
    ma_id: str
    baseline_method: MethodName
    comparator_method: MethodName
    tier1_sig_flip: bool | None
    tier2_direction_flip: bool | None
    tier3_mid_flip: bool | None
    reason_code: ReasonCode
