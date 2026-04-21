"""Aggregator tests — stratification, dual denominators, sparse flag, markdown."""
from __future__ import annotations

import pandas as pd
import pytest

from src.aggregator import (
    DENOM_COMPARABLE,
    DENOM_TOTAL,
    aggregate_flips,
    k_stratum,
    overall_flip_rate,
    to_markdown,
)
from src.ma_types import FlipResult


def test_k_stratum_boundaries() -> None:
    assert k_stratum(1) == "k<5"
    assert k_stratum(4) == "k<5"
    assert k_stratum(5) == "5<=k<10"
    assert k_stratum(9) == "5<=k<10"
    assert k_stratum(10) == "10<=k<20"
    assert k_stratum(19) == "10<=k<20"
    assert k_stratum(20) == "k>=20"
    assert k_stratum(1000) == "k>=20"


def _flip(ma_id: str, t1: bool | None = False, t2: bool | None = False,
          t3: bool | None = None, reason: str = "") -> FlipResult:
    return FlipResult(
        ma_id=ma_id, baseline_method="DL", comparator_method="REML_HKSJ_PI",
        tier1_sig_flip=t1, tier2_direction_flip=t2, tier3_mid_flip=t3,
        reason_code=reason,
    )


def _meta(n: int, outcome_type: str = "binary",
          reproducibility_status: str = "reproducible",
          k: int = 5) -> pd.DataFrame:
    return pd.DataFrame({
        "ma_id": [f"ma_{i}" for i in range(n)],
        "outcome_type": [outcome_type] * n,
        "reproducibility_status": [reproducibility_status] * n,
        "k": [k] * n,
    })


def test_aggregate_reports_both_denominators() -> None:
    # 3 MAs: 1 flip, 1 no-flip, 1 NA (unconverged)
    flips = [
        _flip("ma_0", t1=True),
        _flip("ma_1", t1=False),
        _flip("ma_2", t1=None, reason="comparator_unconverged"),
    ]
    meta = _meta(3)
    df = aggregate_flips(flips, meta, tier="tier1_sig_flip")
    assert len(df) == 1
    row = df.iloc[0]
    assert row[DENOM_TOTAL] == 3
    assert row[DENOM_COMPARABLE] == 2
    assert row["n_flips"] == 1
    assert row["flip_rate_comparable"] == pytest.approx(0.5)
    assert row["flip_rate_total"] == pytest.approx(1 / 3)


def test_aggregate_strata_split() -> None:
    flips = [_flip(f"ma_{i}", t1=(i % 2 == 0)) for i in range(20)]
    # 10 binary k=3, 10 continuous k=15
    meta = pd.DataFrame({
        "ma_id": [f"ma_{i}" for i in range(20)],
        "outcome_type": ["binary"] * 10 + ["continuous"] * 10,
        "reproducibility_status": ["reproducible"] * 20,
        "k": [3] * 10 + [15] * 10,
    })
    df = aggregate_flips(flips, meta, tier="tier1_sig_flip")
    assert len(df) == 2
    by_k = df.set_index("k_stratum")
    assert by_k.loc["k<5", DENOM_TOTAL] == 10
    assert by_k.loc["10<=k<20", DENOM_TOTAL] == 10


def test_aggregate_sparse_stratum_flag() -> None:
    flips = [_flip(f"ma_{i}", t1=True) for i in range(5)]
    meta = _meta(5)
    df = aggregate_flips(flips, meta, tier="tier1_sig_flip")
    assert df["sparse_stratum"].iloc[0] is True or df["sparse_stratum"].iloc[0] == True  # noqa: E712


def test_aggregate_non_sparse_for_large_stratum() -> None:
    flips = [_flip(f"ma_{i}", t1=(i % 4 == 0)) for i in range(50)]
    meta = _meta(50)
    df = aggregate_flips(flips, meta, tier="tier1_sig_flip")
    assert bool(df["sparse_stratum"].iloc[0]) is False


def test_aggregate_all_na_yields_nan_rate_but_counts_in_total() -> None:
    flips = [_flip(f"ma_{i}", t1=None, reason="comparator_unconverged") for i in range(10)]
    meta = _meta(10)
    df = aggregate_flips(flips, meta, tier="tier1_sig_flip")
    row = df.iloc[0]
    assert row[DENOM_TOTAL] == 10
    assert row[DENOM_COMPARABLE] == 0
    assert row["n_flips"] == 0
    assert pd.isna(row["flip_rate_comparable"])
    assert row["flip_rate_total"] == pytest.approx(0.0)


def test_aggregate_empty_returns_empty_frame() -> None:
    df = aggregate_flips([], pd.DataFrame(columns=["ma_id", "outcome_type",
                                                   "reproducibility_status", "k"]),
                          tier="tier1_sig_flip")
    assert df.empty
    assert DENOM_TOTAL in df.columns


def test_tier3_mid_flip_aggregation() -> None:
    """Tier 3 commonly has many NAs (outcome not in MID table)."""
    flips = [
        _flip("ma_0", t3=True),
        _flip("ma_1", t3=False),
        _flip("ma_2", t3=None),  # outcome not in MID table
    ]
    meta = _meta(3)
    df = aggregate_flips(flips, meta, tier="tier3_mid_flip")
    row = df.iloc[0]
    assert row[DENOM_TOTAL] == 3
    assert row[DENOM_COMPARABLE] == 2  # the NA is excluded from comparable
    assert row["n_flips"] == 1
    assert row["flip_rate_comparable"] == pytest.approx(0.5)


# --- Overall rate + markdown export ---

def test_overall_flip_rate_uses_weighted_sum() -> None:
    """overall_rate = sum(n_flips) / sum(n_comparable), NOT mean of rates.
    Two strata: (2 flips / 4) and (1 flip / 100). Weighted = 3/104 ≈ 0.029,
    not mean-of-rates = (0.5 + 0.01)/2 = 0.255."""
    df = pd.DataFrame([
        {"reproducibility_status": "reproducible", "outcome_type": "binary",
         "k_stratum": "k<5", DENOM_TOTAL: 4, DENOM_COMPARABLE: 4, "n_flips": 2,
         "flip_rate_comparable": 0.5, "flip_rate_total": 0.5, "sparse_stratum": True},
        {"reproducibility_status": "reproducible", "outcome_type": "continuous",
         "k_stratum": "k>=20", DENOM_TOTAL: 100, DENOM_COMPARABLE: 100, "n_flips": 1,
         "flip_rate_comparable": 0.01, "flip_rate_total": 0.01, "sparse_stratum": False},
    ])
    assert overall_flip_rate(df) == pytest.approx(3 / 104)


def test_overall_flip_rate_empty_returns_nan() -> None:
    assert pd.isna(overall_flip_rate(pd.DataFrame()))


def test_to_markdown_nonempty() -> None:
    flips = [_flip(f"ma_{i}", t1=(i % 2 == 0)) for i in range(10)]
    meta = _meta(10)
    df = aggregate_flips(flips, meta, tier="tier1_sig_flip")
    md = to_markdown(df)
    assert "|" in md
    assert "flip_rate_comparable" in md


def test_to_markdown_empty_renders_placeholder() -> None:
    """Sentinel P1-empty-dataframe-access rule: don't crash on empty."""
    md = to_markdown(pd.DataFrame())
    assert "No data" in md
