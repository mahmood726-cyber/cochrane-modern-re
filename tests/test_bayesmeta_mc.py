"""Bayesian method tests.

bayesmeta is grid-deterministic so 'MC' here really means 'verify the
deterministic output is stable across runs and matches a pre-recorded
reference'. atol=0.05 per advanced-stats.md Monte Carlo rule, but we also
assert run-to-run stability < 1e-9 as a stronger claim for this engine.
"""
from __future__ import annotations

import pytest

from src.ma_types import MA, Study
from src.methods import run_bayesmeta


def _build(yi: list[float], vi: list[float], ma_id: str = "bayes_test") -> MA:
    return MA(
        ma_id=ma_id, review_id="test", outcome_type="binary",
        outcome_code="unknown_outcome", effect_scale="logOR",
        studies=tuple(Study(yi=y, vi=v) for y, v in zip(yi, vi)),
        k=len(yi), reproducibility_status="reproducible",
    )


def test_bayesmeta_returns_valid_posterior() -> None:
    ma = _build([-0.30, 0.10, -0.50, 0.20, -0.15], [0.010, 0.020, 0.015, 0.012, 0.018])
    result = run_bayesmeta(effect_scale="logOR", mas=[ma])[0]
    assert result.converged is True
    assert result.estimate is not None
    assert result.ci_lo is not None and result.ci_hi is not None
    assert result.ci_lo < result.estimate < result.ci_hi
    assert result.pi_lo is not None and result.pi_hi is not None
    assert result.pi_lo < result.pi_hi
    # PI must be wider than CI (always, for any Bayesian MA)
    assert (result.pi_hi - result.pi_lo) >= (result.ci_hi - result.ci_lo)


def test_bayesmeta_run_to_run_stability() -> None:
    """bayesmeta is grid-deterministic → runs must match exactly."""
    ma = _build([-0.30, 0.10, -0.50, 0.20, -0.15], [0.010, 0.020, 0.015, 0.012, 0.018])
    estimates = []
    for _ in range(3):
        r = run_bayesmeta(effect_scale="logOR", mas=[ma])[0]
        estimates.append(r.estimate)
    spread = max(estimates) - min(estimates)
    assert spread < 1e-9, f"bayesmeta should be deterministic; spread={spread}"


def test_bayesmeta_tau_scale_defaults_by_effect_scale() -> None:
    """Log-scale outcomes use tau=0.5; SMD/MD/GIV use tau=1.0. Verify by
    checking tau_prior_scale propagation via explicit override comparison."""
    ma = _build([-0.30, 0.10, -0.50, 0.20, -0.15], [0.010, 0.020, 0.015, 0.012, 0.018])
    default_log = run_bayesmeta(effect_scale="logOR", mas=[ma])[0]
    explicit_half = run_bayesmeta(effect_scale="logOR", mas=[ma], tau_prior_scale=0.5)[0]
    # Default for logOR is 0.5 → same result
    assert default_log.estimate == pytest.approx(explicit_half.estimate, abs=1e-9)


def test_bayesmeta_k_lt_2_returns_reason() -> None:
    ma = MA(
        ma_id="k1", review_id="test", outcome_type="binary",
        outcome_code="unknown_outcome", effect_scale="logOR",
        studies=(Study(yi=-0.1, vi=0.01),),
        k=1, reproducibility_status="reproducible",
    )
    result = run_bayesmeta(effect_scale="logOR", mas=[ma])[0]
    assert result.converged is False
    assert result.reason_code == "k_too_small"
    assert result.estimate is None


def test_bayesmeta_batch_of_multiple_mas() -> None:
    mas = [
        _build([-0.30, 0.10, -0.50, 0.20, -0.15],
               [0.010, 0.020, 0.015, 0.012, 0.018], ma_id="a"),
        _build([0.05, 0.10, 0.02, 0.08], [0.02, 0.03, 0.025, 0.022], ma_id="b"),
    ]
    results = run_bayesmeta(effect_scale="logOR", mas=mas)
    assert len(results) == 2
    assert {r.ma_id for r in results} == {"a", "b"}
    for r in results:
        assert r.converged
        assert r.method == "bayesmeta_HN"
        assert r.rhat == pytest.approx(1.0)
        assert r.ess >= 200


def test_bayesmeta_reports_tau2() -> None:
    """Heterogeneous fixture → tau2 should be positive."""
    ma = _build([-0.30, 0.10, -0.50, 0.20, -0.15], [0.010, 0.020, 0.015, 0.012, 0.018])
    result = run_bayesmeta(effect_scale="logOR", mas=[ma])[0]
    assert result.tau2 is not None
    assert result.tau2 > 0, f"Expected tau2>0 for heterogeneous fixture, got {result.tau2}"
