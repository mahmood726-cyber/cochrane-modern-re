"""Static single-file HTML dashboard.

Renders cross-tabs from the aggregator as a Pages-deployable index.html
with no external CDN. Pattern matches repro-floor-atlas.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _render_table_html(df: pd.DataFrame) -> str:
    """Render a cross-tab as HTML. Empty DF → inline placeholder
    (Sentinel P1-empty-dataframe-access rule)."""
    if df.empty:
        return '<p class="sparse">— No data in this stratum —</p>'

    display = df.drop(columns=["sparse_stratum"], errors="ignore").copy()
    # Nice column labels
    display.columns = [c.replace("_", " ") for c in display.columns]
    return display.to_html(index=False, float_format=lambda x: f"{x:.3f}", border=0,
                           na_rep="—")


def build_dashboard(
    *,
    tier1_df: pd.DataFrame,
    tier2_df: pd.DataFrame,
    tier3_df: pd.DataFrame,
    headline_rate: float,
    n_mas: int,
    n_reviews: int,
    version: str,
    output: Path,
    comparator_description: str = "DL baseline vs REML+HKSJ+PI modern RE",
) -> None:
    """Write index.html to `output`."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("dashboard.html.j2")
    html = tmpl.render(
        tier1_table=_render_table_html(tier1_df),
        tier2_table=_render_table_html(tier2_df),
        tier3_table=_render_table_html(tier3_df),
        headline_rate=float(headline_rate) if headline_rate == headline_rate else 0.0,
        n_mas=n_mas,
        n_reviews=n_reviews,
        version=version,
        comparator_description=comparator_description,
        generated_at=_dt.datetime.now(_dt.UTC).isoformat(timespec="minutes"),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
