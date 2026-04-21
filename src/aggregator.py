"""Stratified flip-rate aggregator.

Produces cross-tabs keyed by (reproducibility_status × outcome_type × k_stratum)
with BOTH denominators reported (comparable_MAs and total_MAs). Sparse strata
flagged but not suppressed. Markdown export for paper/tables.
"""
from __future__ import annotations

from typing import Literal

import pandas as pd

from src.ma_types import FlipResult

DENOM_COMPARABLE = "n_comparable"
DENOM_TOTAL = "n_total"
SPARSE_THRESHOLD = 20

Tier = Literal["tier1_sig_flip", "tier2_direction_flip", "tier3_mid_flip"]


def k_stratum(k: int) -> str:
    """Bin study counts into strata matching DL-bias guidance (advanced-stats.md).

    The k<5 and 5<=k<10 strata are where DL bias is worst; we expect the
    largest flip rates there when comparing DL vs REML+HKSJ+PI.
    """
    if k < 5:
        return "k<5"
    if k < 10:
        return "5<=k<10"
    if k < 20:
        return "10<=k<20"
    return "k>=20"


def aggregate_flips(
    flips: list[FlipResult],
    meta: pd.DataFrame,
    *,
    tier: Tier,
) -> pd.DataFrame:
    """Build a stratified cross-tab for one tier.

    Parameters
    ----------
    flips
        List of FlipResult records (one per MA per baseline-comparator pair).
    meta
        DataFrame with columns: ma_id, outcome_type, reproducibility_status, k.
        Must have one row per ma_id.
    tier
        Which flip tier to aggregate ('tier1_sig_flip', 'tier2_direction_flip',
        or 'tier3_mid_flip').

    Returns a DataFrame with one row per (reproducibility_status,
    outcome_type, k_stratum) cell, columns:
        n_total — total MAs in stratum
        n_comparable — MAs where flip is True/False (not NA)
        n_flips — MAs where flip is True
        flip_rate_comparable — n_flips / n_comparable (may be NaN if 0)
        flip_rate_total — n_flips / n_total
        sparse_stratum — True if n_total < 20
    """
    if not flips:
        return pd.DataFrame(columns=[
            "reproducibility_status", "outcome_type", "k_stratum",
            DENOM_TOTAL, DENOM_COMPARABLE, "n_flips",
            "flip_rate_comparable", "flip_rate_total", "sparse_stratum",
        ])

    flip_df = pd.DataFrame([
        {"ma_id": f.ma_id, "flip": getattr(f, tier)} for f in flips
    ])
    if "ma_id" not in meta.columns:
        raise ValueError("meta DataFrame must have a 'ma_id' column")
    joined = meta.merge(flip_df, on="ma_id", how="left")
    joined["k_stratum"] = joined["k"].apply(k_stratum)

    group_cols = ["reproducibility_status", "outcome_type", "k_stratum"]

    rows: list[dict] = []
    for keys, group in joined.groupby(group_cols, dropna=False):
        comparable = group["flip"].dropna()
        n_comp = len(comparable)
        n_flips = int((comparable == True).sum())  # noqa: E712  (explicit bool match)
        n_total = len(group)
        rows.append({
            "reproducibility_status": keys[0],
            "outcome_type": keys[1],
            "k_stratum": keys[2],
            DENOM_TOTAL: n_total,
            DENOM_COMPARABLE: n_comp,
            "n_flips": n_flips,
            "flip_rate_comparable": (n_flips / n_comp) if n_comp else float("nan"),
            "flip_rate_total": (n_flips / n_total) if n_total else float("nan"),
            "sparse_stratum": n_total < SPARSE_THRESHOLD,
        })
    return pd.DataFrame(rows).sort_values(group_cols).reset_index(drop=True)


def to_markdown(df: pd.DataFrame) -> str:
    """Render cross-tab as Pandoc-friendly markdown for paper/tables.

    Guards against empty DataFrame (Sentinel P1-empty-dataframe-access rule).
    """
    if df.empty:
        return "_No data in this stratum._"
    return df.to_markdown(index=False, floatfmt=".3f")


def overall_flip_rate(df: pd.DataFrame) -> float:
    """Corpus-wide flip rate on comparable MAs. NaN if no comparable MAs.

    Uses `n_flips.sum() / n_comparable.sum()` — the correctly-weighted overall
    rate, not the mean of per-stratum rates.
    """
    if df.empty:
        return float("nan")
    total_comp = df[DENOM_COMPARABLE].sum()
    total_flips = df["n_flips"].sum()
    return (total_flips / total_comp) if total_comp else float("nan")
