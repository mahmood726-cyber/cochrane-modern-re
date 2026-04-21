"""Dashboard tests — HTML renders, empty-DF guarded, version & corpus stats surfaced."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.dashboard import build_dashboard


def _populated_df(rate: float = 0.126) -> pd.DataFrame:
    return pd.DataFrame([{
        "reproducibility_status": "reproducible",
        "outcome_type": "binary",
        "k_stratum": "5<=k<10",
        "n_total": 100, "n_comparable": 95, "n_flips": 12,
        "flip_rate_comparable": rate, "flip_rate_total": rate * 0.95,
        "sparse_stratum": False,
    }])


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "reproducibility_status", "outcome_type", "k_stratum",
        "n_total", "n_comparable", "n_flips",
        "flip_rate_comparable", "flip_rate_total", "sparse_stratum",
    ])


def test_dashboard_renders_all_three_tiers(tmp_path: Path) -> None:
    out = tmp_path / "index.html"
    build_dashboard(
        tier1_df=_populated_df(0.126),
        tier2_df=_populated_df(0.008),
        tier3_df=_populated_df(0.045),
        headline_rate=0.126,
        n_mas=7545, n_reviews=595,
        version="0.1.0",
        output=out,
    )
    html = out.read_text(encoding="utf-8")
    assert "Flip Atlas" in html
    assert "7545" in html
    assert "595" in html
    assert "12.6%" in html
    assert "Tier 1" in html
    assert "Tier 2" in html
    assert "Tier 3" in html
    assert "v0.1.0" in html


def test_dashboard_handles_empty_stratum_tables(tmp_path: Path) -> None:
    """P1-empty-dataframe-access: no .iloc on empty DF."""
    out = tmp_path / "index.html"
    build_dashboard(
        tier1_df=_empty_df(), tier2_df=_empty_df(), tier3_df=_empty_df(),
        headline_rate=0.0, n_mas=0, n_reviews=0, version="0.1.0-dev", output=out,
    )
    html = out.read_text(encoding="utf-8")
    assert "Flip Atlas" in html
    assert "No data" in html


def test_dashboard_creates_parent_directory(tmp_path: Path) -> None:
    """build_dashboard() should mkdir parent if missing."""
    out = tmp_path / "nested" / "dir" / "index.html"
    build_dashboard(
        tier1_df=_populated_df(), tier2_df=_populated_df(), tier3_df=_populated_df(),
        headline_rate=0.1, n_mas=100, n_reviews=10, version="0.1.0", output=out,
    )
    assert out.exists()


def test_dashboard_drops_sparse_stratum_column_from_table(tmp_path: Path) -> None:
    """sparse_stratum is internal metadata; the rendered HTML shouldn't display it."""
    sparse_df = pd.DataFrame([{
        "reproducibility_status": "reproducible",
        "outcome_type": "binary",
        "k_stratum": "k<5",
        "n_total": 3, "n_comparable": 3, "n_flips": 1,
        "flip_rate_comparable": 0.333, "flip_rate_total": 0.333,
        "sparse_stratum": True,
    }])
    out = tmp_path / "index.html"
    build_dashboard(
        tier1_df=sparse_df, tier2_df=sparse_df, tier3_df=sparse_df,
        headline_rate=0.333, n_mas=3, n_reviews=1, version="0.1.0", output=out,
    )
    html = out.read_text(encoding="utf-8")
    # The internal sparse_stratum column should not appear as a <th>
    assert "<th>sparse stratum</th>" not in html
    # But the data itself is rendered
    assert "0.333" in html


def test_dashboard_nan_headline_rate_does_not_crash(tmp_path: Path) -> None:
    out = tmp_path / "index.html"
    build_dashboard(
        tier1_df=_empty_df(), tier2_df=_empty_df(), tier3_df=_empty_df(),
        headline_rate=float("nan"), n_mas=0, n_reviews=0,
        version="0.1.0-dev", output=out,
    )
    html = out.read_text(encoding="utf-8")
    assert "Flip Atlas" in html
