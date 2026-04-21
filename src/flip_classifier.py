"""3-tier flip classifier.

Tier 1: significance flip (CI includes-vs-excludes null).
Tier 2: direction flip (sign of point estimate changes).
Tier 3: clinically-important flip (|Δ estimate| > MID for outcome). Scale-aware:
        for ratio outcomes (logRR/logOR/logHR), Δ is compared on natural scale
        via back-transform; for continuous (SMD/MD/GIV), direct comparison.

Returns FlipResult with None for any tier that is NA for structural reasons
(missing comparator, outcome not in MID table, baseline unconverged, etc.).
Never a silent-failure sentinel string.
"""
from __future__ import annotations

import math

from src.ma_types import FlipResult, MethodResult

_RATIO_SCALES = frozenset({"logRR", "logOR", "logHR"})


def _is_significant_at_alpha_05(ci_lo: float | None, ci_hi: float | None) -> bool | None:
    """True if CI excludes the null (0). None if CI bounds are missing."""
    if ci_lo is None or ci_hi is None:
        return None
    return not (ci_lo <= 0 <= ci_hi)


def _tier1_significance_flip(baseline: MethodResult, comparator: MethodResult) -> bool | None:
    base_sig = _is_significant_at_alpha_05(baseline.ci_lo, baseline.ci_hi)
    comp_sig = _is_significant_at_alpha_05(comparator.ci_lo, comparator.ci_hi)
    if base_sig is None or comp_sig is None:
        return None
    return base_sig != comp_sig


def _tier2_direction_flip(baseline: MethodResult, comparator: MethodResult) -> bool | None:
    if baseline.estimate is None or comparator.estimate is None:
        return None
    b, c = baseline.estimate, comparator.estimate
    if b == 0 or c == 0:
        # Exact-zero estimate is a degenerate case; treat as "no direction"
        return False
    return (b > 0) != (c > 0)


def _tier3_mid_flip(
    baseline: MethodResult, comparator: MethodResult,
    effect_scale: str, outcome_code: str, mid_table: dict[str, dict],
) -> bool | None:
    if outcome_code not in mid_table:
        return None
    if baseline.estimate is None or comparator.estimate is None:
        return None
    entry = mid_table[outcome_code]
    mid = float(entry["mid"])
    if effect_scale in _RATIO_SCALES:
        # Natural-scale comparison for ratio outcomes
        delta = abs(math.exp(baseline.estimate) - math.exp(comparator.estimate))
    else:
        # Direct comparison for continuous outcomes (SMD, MD, GIV)
        delta = abs(baseline.estimate - comparator.estimate)
    return delta > mid


def classify_flip(
    baseline: MethodResult,
    comparator: MethodResult,
    *,
    effect_scale: str,
    outcome_code: str,
    mid_table: dict[str, dict],
) -> FlipResult:
    """Classify one baseline-vs-comparator flip triple for a single MA.

    Convergence handling:
      - baseline unconverged OR missing estimate → all tiers NA,
        reason_code='comparison_unavailable'.
      - baseline converged, comparator unconverged → all tiers NA,
        reason_code='comparator_unconverged'. (We don't claim agreement
        where the comparator actually failed.)
      - both converged → classify all 3 tiers; reason_code=''.
    """
    ma_id = baseline.ma_id
    if not baseline.converged or baseline.estimate is None:
        return FlipResult(
            ma_id=ma_id,
            baseline_method=baseline.method,
            comparator_method=comparator.method,
            tier1_sig_flip=None, tier2_direction_flip=None, tier3_mid_flip=None,
            reason_code="comparison_unavailable",
        )
    if not comparator.converged or comparator.estimate is None:
        return FlipResult(
            ma_id=ma_id,
            baseline_method=baseline.method,
            comparator_method=comparator.method,
            tier1_sig_flip=None, tier2_direction_flip=None, tier3_mid_flip=None,
            reason_code="comparator_unconverged",
        )

    return FlipResult(
        ma_id=ma_id,
        baseline_method=baseline.method,
        comparator_method=comparator.method,
        tier1_sig_flip=_tier1_significance_flip(baseline, comparator),
        tier2_direction_flip=_tier2_direction_flip(baseline, comparator),
        tier3_mid_flip=_tier3_mid_flip(baseline, comparator, effect_scale, outcome_code, mid_table),
        reason_code="",
    )
