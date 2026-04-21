"""Run all 4 methods on every MA in the Pairwise70 cache.

Output: outputs/method_results.parquet with one row per (ma_id, method).

Usage:
    python analysis/01_run_methods.py                            # full corpus (slow)
    python analysis/01_run_methods.py --max-reviews 20           # quick subset
    python analysis/01_run_methods.py --subset non_reproducible  # only non-repro MAs
    python analysis/01_run_methods.py --skip-bayes               # faster dev iteration
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

import click
import pandas as pd

from src.loaders import iter_mas_with_log
from src.methods import run_batch, run_bayesmeta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@click.command()
@click.option("--out", type=click.Path(path_type=Path),
              default=Path("outputs/method_results.parquet"))
@click.option("--subset", type=click.Choice(["all", "non_reproducible", "reproducible"]),
              default="all")
@click.option("--max-reviews", type=int, default=None,
              help="Limit to first N reviews (for dev / smoke runs)")
@click.option("--skip-bayes", is_flag=True,
              help="Skip bayesmeta (faster; for dev iteration)")
def main(out: Path, subset: str, max_reviews: int | None, skip_bayes: bool) -> None:
    result = iter_mas_with_log(max_reviews=max_reviews)
    mas = result.mas
    if subset != "all":
        mas = [m for m in mas if m.reproducibility_status == subset]
    logger.info("loaded %d MAs (subset=%s, skipped=%d at load)",
                len(mas), subset, len(result.skip_log))

    by_scale: dict[str, list] = {}
    for m in mas:
        by_scale.setdefault(m.effect_scale, []).append(m)

    rows: list[dict] = []
    for scale, group in by_scale.items():
        logger.info("scale=%s n=%d", scale, len(group))
        for method in ("DL", "REML_only", "REML_HKSJ_PI"):
            for r in run_batch(method=method, effect_scale=scale, mas=group):
                rows.append(asdict(r))
        if not skip_bayes:
            logger.info("  bayesmeta on %s (slow)...", scale)
            for r in run_bayesmeta(effect_scale=scale, mas=group):
                rows.append(asdict(r))

    df = pd.DataFrame(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    logger.info("wrote %d rows to %s", len(df), out)
    logger.info("  converged/total by method:")
    for method, g in df.groupby("method"):
        logger.info("    %s: %d / %d (%.1f%%)",
                    method, g["converged"].sum(), len(g),
                    100 * g["converged"].sum() / max(len(g), 1))


if __name__ == "__main__":
    main()
