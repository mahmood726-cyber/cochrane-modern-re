"""Method-runner tests — 1e-6 validation against metafor.

Covers Tasks 3.2 (wrapper validation), 3.3 (HKSJ floor), 3.4 (k boundaries).
Expected values pre-computed in tests/fixtures/expected_metafor.json by
scripts/generate_expected.R — regenerate that file if the method set changes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ma_types import MA, Study
from src.methods import run_batch

METHODS = ("DL", "REML_only", "REML_HKSJ_PI")


def _build_ma(ma_id: str, yi: list[float], vi: list[float]) -> MA:
    return MA(
        ma_id=ma_id, review_id="test", outcome_type="binary",
        outcome_code="unknown_outcome", effect_scale="logOR",
        studies=tuple(Study(yi=y, vi=v) for y, v in zip(yi, vi)),
        k=len(yi), reproducibility_status="reproducible",
    )


@pytest.fixture(scope="module")
def expected(fixtures_dir: Path) -> dict:
    with (fixtures_dir / "expected_metafor.json").open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("method", METHODS)
def test_binary_k5_heterogeneous_matches_metafor(method: str, expected: dict) -> None:
    """Heterogeneous fixture: Q > k-1 so HKSJ floor does not bind.
    Expected wrapper output matches raw metafor at 1e-6."""
    fx = expected["binary_k5_heterogeneous"][method]
    ma = _build_ma(
        "binary_k5_heterogeneous",
        [-0.30, 0.10, -0.50, 0.20, -0.15],
        [0.010, 0.020, 0.015, 0.012, 0.018],
    )
    result = run_batch(method=method, effect_scale="logOR", mas=[ma])[0]
    assert result.converged
    assert result.estimate == pytest.approx(fx["estimate"], abs=1e-6)
    assert result.se == pytest.approx(fx["se"], abs=1e-6)
    assert result.ci_lo == pytest.approx(fx["ci_lo"], abs=1e-6)
    assert result.ci_hi == pytest.approx(fx["ci_hi"], abs=1e-6)
    assert result.tau2 == pytest.approx(fx["tau2"], abs=1e-6)


def test_pi_populated_for_k_ge_3(expected: dict) -> None:
    fx = expected["binary_k3_moderate_het"]["REML_HKSJ_PI"]
    ma = _build_ma("binary_k3_moderate_het", [-0.30, 0.10, -0.20], [0.05, 0.07, 0.06])
    result = run_batch(method="REML_HKSJ_PI", effect_scale="logOR", mas=[ma])[0]
    if fx["pi_lo"] is None:
        assert result.pi_lo is None
    else:
        assert result.pi_lo == pytest.approx(fx["pi_lo"], abs=1e-6)
        assert result.pi_hi == pytest.approx(fx["pi_hi"], abs=1e-6)


def test_pi_na_for_k_2() -> None:
    """Task 3.4 boundary: PI uses t_{k-2}; undefined for k<3."""
    ma = _build_ma("k2_boundary", [-0.10, 0.20], [0.02, 0.025])
    result = run_batch(method="REML_HKSJ_PI", effect_scale="logOR", mas=[ma])[0]
    assert result.converged is True
    assert result.estimate is not None
    assert result.pi_lo is None
    assert result.pi_hi is None


def test_k_lt_2_returns_reason_code() -> None:
    """Task 3.4: k<2 → all methods NA with reason 'k_too_small'."""
    ma = _build_ma("k1", [-0.1], [0.01])
    result = run_batch(method="DL", effect_scale="logOR", mas=[ma])[0]
    assert result.converged is False
    assert result.reason_code == "k_too_small"
    assert result.estimate is None


def test_continuous_k10_fixture_matches(expected: dict) -> None:
    fx = expected["continuous_k10_mixed"]["REML_HKSJ_PI"]
    yi = [0.20, 0.25, -0.10, 0.15, 0.40, 0.05, 0.50, -0.05, 0.30, 0.00]
    vi = [0.05] * 10
    ma = MA(
        ma_id="continuous_k10_mixed", review_id="test", outcome_type="continuous",
        outcome_code="unknown_outcome", effect_scale="MD",
        studies=tuple(Study(yi=y, vi=v) for y, v in zip(yi, vi)),
        k=len(yi), reproducibility_status="reproducible",
    )
    result = run_batch(method="REML_HKSJ_PI", effect_scale="MD", mas=[ma])[0]
    assert result.estimate == pytest.approx(fx["estimate"], abs=1e-6)
    assert result.se == pytest.approx(fx["se"], abs=1e-6)


def test_hksj_floor_prevents_narrowing_below_dl() -> None:
    """Task 3.3: HKSJ floor rule — when Q/(k-1)<1, CI must not narrow below DL.

    The fixture `hksj_narrow_homogeneous` has near-homogeneous studies with
    low Q; without the floor, HKSJ SE can be smaller than DL SE. With the
    floor (which metafor's test='knha' applies natively), HKSJ SE ≥ DL SE.
    """
    yi = [-0.100, -0.101, -0.099, -0.100, -0.102]
    vi = [0.010] * 5
    ma = _build_ma("hksj_floor_check", yi, vi)
    dl = run_batch(method="DL", effect_scale="logOR", mas=[ma])[0]
    hksj = run_batch(method="REML_HKSJ_PI", effect_scale="logOR", mas=[ma])[0]
    dl_width = dl.ci_hi - dl.ci_lo
    hksj_width = hksj.ci_hi - hksj.ci_lo
    # Floor guarantees HKSJ CI is NOT narrower than DL
    assert hksj_width >= dl_width - 1e-9, (
        f"HKSJ narrower than DL: DL_width={dl_width}, HKSJ_width={hksj_width}"
    )


def test_batch_of_multiple_mas() -> None:
    """Validate batching: one R subprocess call handles multiple MAs correctly."""
    mas = [
        _build_ma("a", [-0.12, -0.18, -0.05, -0.22, -0.10],
                  [0.010, 0.015, 0.020, 0.008, 0.012]),
        _build_ma("b", [-0.30, -0.20, -0.25], [0.05, 0.07, 0.06]),
        _build_ma("c", [-0.10, -0.15], [0.02, 0.025]),
    ]
    results = run_batch(method="DL", effect_scale="logOR", mas=mas)
    assert len(results) == 3
    by_id = {r.ma_id: r for r in results}
    assert by_id["a"].k_effective == 5
    assert by_id["b"].k_effective == 3
    assert by_id["c"].k_effective == 2
    for r in results:
        assert r.converged
        assert r.estimate is not None


def test_empty_batch_returns_empty_list() -> None:
    assert run_batch(method="DL", effect_scale="logOR", mas=[]) == []
