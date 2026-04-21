"""Flip classifier tests — 3 tiers + NA propagation."""
from __future__ import annotations

import pytest

from src.flip_classifier import classify_flip
from src.ma_types import MethodResult


def _result(
    method: str = "DL",
    estimate: float | None = None,
    ci_lo: float | None = None,
    ci_hi: float | None = None,
    converged: bool = True,
    ma_id: str = "x",
) -> MethodResult:
    return MethodResult(
        ma_id=ma_id, method=method,
        estimate=estimate,
        se=0.05 if estimate is not None else None,
        ci_lo=ci_lo, ci_hi=ci_hi,
        tau2=0.01, i2=50.0, pi_lo=None, pi_hi=None,
        k_effective=5, converged=converged,
        rhat=None, ess=None,
        reason_code="" if converged else "bayes_unconverged",
    )


# --- Tier 1 ---

def test_tier1_sig_to_nonsig() -> None:
    base = _result(estimate=-0.15, ci_lo=-0.25, ci_hi=-0.05)  # sig (excludes 0)
    comp = _result(method="REML_HKSJ_PI", estimate=-0.15, ci_lo=-0.30, ci_hi=0.02)  # non-sig
    flip = classify_flip(base, comp, effect_scale="logOR", outcome_code="any", mid_table={})
    assert flip.tier1_sig_flip is True


def test_tier1_nonsig_to_sig() -> None:
    base = _result(estimate=-0.15, ci_lo=-0.30, ci_hi=0.02)  # non-sig
    comp = _result(method="REML_HKSJ_PI", estimate=-0.15, ci_lo=-0.25, ci_hi=-0.05)  # sig
    flip = classify_flip(base, comp, effect_scale="logOR", outcome_code="any", mid_table={})
    assert flip.tier1_sig_flip is True


def test_tier1_no_flip_both_sig() -> None:
    base = _result(estimate=-0.15, ci_lo=-0.25, ci_hi=-0.05)
    comp = _result(method="REML_HKSJ_PI", estimate=-0.14, ci_lo=-0.24, ci_hi=-0.04)
    flip = classify_flip(base, comp, effect_scale="logOR", outcome_code="any", mid_table={})
    assert flip.tier1_sig_flip is False


def test_tier1_no_flip_both_nonsig() -> None:
    base = _result(estimate=-0.05, ci_lo=-0.15, ci_hi=0.05)
    comp = _result(method="REML_HKSJ_PI", estimate=-0.04, ci_lo=-0.18, ci_hi=0.10)
    flip = classify_flip(base, comp, effect_scale="logOR", outcome_code="any", mid_table={})
    assert flip.tier1_sig_flip is False


# --- Tier 2 ---

def test_tier2_direction_flip() -> None:
    base = _result(estimate=-0.15, ci_lo=-0.25, ci_hi=-0.05)
    comp = _result(method="REML_HKSJ_PI", estimate=0.02, ci_lo=-0.10, ci_hi=0.14)
    flip = classify_flip(base, comp, effect_scale="logOR", outcome_code="any", mid_table={})
    assert flip.tier2_direction_flip is True


def test_tier2_no_direction_flip_same_sign() -> None:
    base = _result(estimate=-0.15, ci_lo=-0.25, ci_hi=-0.05)
    comp = _result(method="REML_HKSJ_PI", estimate=-0.05, ci_lo=-0.15, ci_hi=0.05)
    flip = classify_flip(base, comp, effect_scale="logOR", outcome_code="any", mid_table={})
    assert flip.tier2_direction_flip is False


def test_tier2_exact_zero_treated_as_no_direction() -> None:
    """Edge case: estimate exactly 0 has no direction; we return False (not None)."""
    base = _result(estimate=-0.15, ci_lo=-0.25, ci_hi=-0.05)
    comp = _result(method="REML_HKSJ_PI", estimate=0.0, ci_lo=-0.10, ci_hi=0.10)
    flip = classify_flip(base, comp, effect_scale="logOR", outcome_code="any", mid_table={})
    assert flip.tier2_direction_flip is False


# --- Tier 3 ---

def test_tier3_ratio_scale_back_transforms() -> None:
    """For ratio outcomes, MID comparison is on natural scale.
    exp(-0.10)=0.905, exp(-0.20)=0.819. Δ=0.086. MID=0.05. → flip=True."""
    base = _result(estimate=-0.10, ci_lo=-0.20, ci_hi=0.00)
    comp = _result(method="REML_HKSJ_PI", estimate=-0.20, ci_lo=-0.30, ci_hi=-0.10)
    mid_table = {"all_cause_mortality": {"mid": 0.05, "scale": "natural", "source": "t"}}
    flip = classify_flip(base, comp, effect_scale="logOR",
                         outcome_code="all_cause_mortality", mid_table=mid_table)
    assert flip.tier3_mid_flip is True


def test_tier3_ratio_below_mid() -> None:
    """exp(-0.10)=0.905, exp(-0.11)=0.896. Δ=0.009. MID=0.05. → no flip."""
    base = _result(estimate=-0.10, ci_lo=-0.20, ci_hi=0.00)
    comp = _result(method="REML_HKSJ_PI", estimate=-0.11, ci_lo=-0.21, ci_hi=-0.01)
    mid_table = {"all_cause_mortality": {"mid": 0.05, "scale": "natural", "source": "t"}}
    flip = classify_flip(base, comp, effect_scale="logOR",
                         outcome_code="all_cause_mortality", mid_table=mid_table)
    assert flip.tier3_mid_flip is False


def test_tier3_continuous_direct_compare() -> None:
    """SMD direct comparison (no back-transform). |0.45-0.20|=0.25 > MID=0.2 → flip."""
    base = _result(estimate=0.20, ci_lo=0.05, ci_hi=0.35)
    comp = _result(method="REML_HKSJ_PI", estimate=0.45, ci_lo=0.30, ci_hi=0.60)
    mid_table = {"sf36_pcs": {"mid": 0.2, "scale": "sd_units", "source": "t"}}
    flip = classify_flip(base, comp, effect_scale="SMD",
                         outcome_code="sf36_pcs", mid_table=mid_table)
    assert flip.tier3_mid_flip is True


def test_tier3_continuous_below_mid() -> None:
    base = _result(estimate=0.20, ci_lo=0.05, ci_hi=0.35)
    comp = _result(method="REML_HKSJ_PI", estimate=0.25, ci_lo=0.10, ci_hi=0.40)
    mid_table = {"sf36_pcs": {"mid": 0.2, "scale": "sd_units", "source": "t"}}
    flip = classify_flip(base, comp, effect_scale="SMD",
                         outcome_code="sf36_pcs", mid_table=mid_table)
    assert flip.tier3_mid_flip is False


def test_tier3_na_when_outcome_missing() -> None:
    base = _result(estimate=-0.10, ci_lo=-0.20, ci_hi=0.00)
    comp = _result(method="REML_HKSJ_PI", estimate=-0.20, ci_lo=-0.30, ci_hi=-0.10)
    flip = classify_flip(base, comp, effect_scale="logOR",
                         outcome_code="not_in_table", mid_table={})
    assert flip.tier3_mid_flip is None


# --- NA propagation ---

def test_baseline_unconverged_comparison_unavailable() -> None:
    base = _result(estimate=None, ci_lo=None, ci_hi=None, converged=False)
    comp = _result(method="REML_HKSJ_PI", estimate=-0.15, ci_lo=-0.25, ci_hi=-0.05)
    flip = classify_flip(base, comp, effect_scale="logOR",
                         outcome_code="all_cause_mortality",
                         mid_table={"all_cause_mortality": {"mid": 0.05, "scale": "natural", "source": "t"}})
    assert flip.reason_code == "comparison_unavailable"
    assert flip.tier1_sig_flip is None
    assert flip.tier2_direction_flip is None
    assert flip.tier3_mid_flip is None


def test_comparator_unconverged_all_na() -> None:
    base = _result(estimate=-0.15, ci_lo=-0.25, ci_hi=-0.05)
    comp = _result(method="bayesmeta_HN", estimate=None, ci_lo=None, ci_hi=None, converged=False)
    flip = classify_flip(base, comp, effect_scale="logOR",
                         outcome_code="all_cause_mortality",
                         mid_table={"all_cause_mortality": {"mid": 0.05, "scale": "natural", "source": "t"}})
    assert flip.reason_code == "comparator_unconverged"
    assert flip.tier1_sig_flip is None
    assert flip.tier2_direction_flip is None
    assert flip.tier3_mid_flip is None


# --- Combined / complex cases ---

def test_clinical_flip_without_significance_flip() -> None:
    """Important paper case: Tier 3 fires but Tier 1 doesn't — the difference is
    clinically meaningful even though neither method reached significance."""
    # Both non-sig (CIs cross 0), but point estimates differ by > MID
    base = _result(estimate=0.02, ci_lo=-0.05, ci_hi=0.09)
    comp = _result(method="REML_HKSJ_PI", estimate=-0.15, ci_lo=-0.30, ci_hi=0.00)
    mid_table = {"mortality": {"mid": 0.05, "scale": "natural", "source": "t"}}
    flip = classify_flip(base, comp, effect_scale="logOR",
                         outcome_code="mortality", mid_table=mid_table)
    assert flip.tier1_sig_flip is False  # both non-sig (comp CI touches 0)
    assert flip.tier2_direction_flip is True   # sign changed
    # exp(0.02)=1.02, exp(-0.15)=0.86 → Δ=0.16 > 0.05
    assert flip.tier3_mid_flip is True
