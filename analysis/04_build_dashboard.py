"""Build the static HTML dashboard at docs/index.html.

Uses DL-vs-REML_HKSJ_PI as the canonical comparator for the dashboard view
(Bayesian comparator is a supplementary analysis, not the headline).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import click
import pandas as pd

from src.dashboard import build_dashboard
from src.loaders import iter_mas_with_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@click.command()
@click.option("--agg-dir", type=click.Path(exists=True, path_type=Path),
              default=Path("outputs"))
@click.option("--out", type=click.Path(path_type=Path),
              default=Path("docs/index.html"))
@click.option("--version", default="0.1.0-dev")
@click.option("--max-reviews", type=int, default=None,
              help="Match the --max-reviews used upstream (for corpus stats)")
@click.option("--comparator", type=click.Choice(["REML_HKSJ_PI", "bayesmeta_HN"]),
              default="REML_HKSJ_PI")
def main(agg_dir: Path, out: Path, version: str, max_reviews: int | None,
         comparator: str) -> None:
    tier1 = pd.read_parquet(agg_dir / f"agg_{comparator}__tier1_sig_flip.parquet")
    tier2 = pd.read_parquet(agg_dir / f"agg_{comparator}__tier2_direction_flip.parquet")
    tier3 = pd.read_parquet(agg_dir / f"agg_{comparator}__tier3_mid_flip.parquet")
    rates = json.loads((agg_dir / "flip_rates_current.json").read_text(encoding="utf-8"))

    # Corpus stats straight from the loader — keeps the dashboard honest
    # about what was actually analysed rather than guessing from aggregation.
    mas = iter_mas_with_log(max_reviews=max_reviews).mas
    n_mas = len(mas)
    n_reviews = len({m.review_id for m in mas})

    headline_key = f"{comparator}__tier1_sig_flip_rate"
    headline_rate = rates.get(headline_key, 0.0)

    descriptions = {
        "REML_HKSJ_PI": "DL baseline vs REML+HKSJ+PI modern RE",
        "bayesmeta_HN": "DL baseline vs Bayesian RE (half-normal prior)",
    }

    build_dashboard(
        tier1_df=tier1, tier2_df=tier2, tier3_df=tier3,
        headline_rate=headline_rate,
        n_mas=n_mas, n_reviews=n_reviews,
        version=version,
        output=out,
        comparator_description=descriptions[comparator],
    )
    logger.info("wrote dashboard: %s (headline=%.3f over %d MAs / %d reviews)",
                out, headline_rate, n_mas, n_reviews)


if __name__ == "__main__":
    main()
