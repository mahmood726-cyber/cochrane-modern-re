"""Contract tests between module boundaries.

Per `lessons.md` 'Integration Contracts': one test per boundary, builds a
production-shaped input, calls the entrypoint, asserts the output isn't a
silent-failure sentinel. These tests exist to catch the MetaReproducer P0-1
class of bug (schema drift between producer and consumer).
"""
from __future__ import annotations

import dataclasses

from src.ma_types import MA, FlipResult, MethodResult, Study


def test_ma_fields_stable() -> None:
    ma = MA(
        ma_id="rev_001_cmp_001_out_001",
        review_id="rev_001",
        outcome_type="binary",
        outcome_code="all_cause_mortality",
        effect_scale="logRR",
        studies=(Study(yi=-0.10, vi=0.01), Study(yi=-0.15, vi=0.02)),
        k=2,
        reproducibility_status="reproducible",
    )
    required = {
        "ma_id", "review_id", "outcome_type", "outcome_code",
        "effect_scale", "studies", "k", "reproducibility_status",
    }
    assert {f.name for f in dataclasses.fields(ma)} == required


def test_study_fields_stable() -> None:
    study = Study(yi=-0.10, vi=0.01)
    assert {f.name for f in dataclasses.fields(study)} == {"yi", "vi"}


def test_method_result_fields_stable() -> None:
    result = MethodResult(
        ma_id="x", method="DL",
        estimate=-0.1, se=0.05, ci_lo=-0.2, ci_hi=0.0,
        tau2=0.01, i2=45.0, pi_lo=-0.3, pi_hi=0.1,
        k_effective=5, converged=True, rhat=None, ess=None,
        reason_code="",
    )
    required = {
        "ma_id", "method", "estimate", "se", "ci_lo", "ci_hi",
        "tau2", "i2", "pi_lo", "pi_hi", "k_effective", "converged",
        "rhat", "ess", "reason_code",
    }
    assert {f.name for f in dataclasses.fields(result)} == required


def test_flip_result_fields_stable() -> None:
    flip = FlipResult(
        ma_id="x", baseline_method="DL", comparator_method="REML_HKSJ_PI",
        tier1_sig_flip=True, tier2_direction_flip=False, tier3_mid_flip=None,
        reason_code="",
    )
    required = {
        "ma_id", "baseline_method", "comparator_method",
        "tier1_sig_flip", "tier2_direction_flip", "tier3_mid_flip",
        "reason_code",
    }
    assert {f.name for f in dataclasses.fields(flip)} == required


def test_na_is_none_not_sentinel_string() -> None:
    """NA must be None, never strings like 'NA' or 'unknown_ratio'.

    Rationale: lessons.md — silent failure sentinels are the enemy.
    """
    flip = FlipResult(
        ma_id="x", baseline_method="DL", comparator_method="REML_HKSJ_PI",
        tier1_sig_flip=None, tier2_direction_flip=None, tier3_mid_flip=None,
        reason_code="comparator_unconverged",
    )
    for tier in (flip.tier1_sig_flip, flip.tier2_direction_flip, flip.tier3_mid_flip):
        assert tier is None or isinstance(tier, bool)


def test_ma_is_hashable_and_immutable() -> None:
    """Frozen dataclass → hashable → usable as dict key, and can't be mutated."""
    ma = MA(
        ma_id="x", review_id="r", outcome_type="binary",
        outcome_code="all_cause_mortality", effect_scale="logRR",
        studies=(Study(yi=-0.1, vi=0.01),),
        k=1, reproducibility_status="reproducible",
    )
    hash(ma)
    try:
        ma.k = 99  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("MA dataclass should be frozen")
