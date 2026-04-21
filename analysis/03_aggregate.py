"""Aggregate flips into stratified cross-tabs per tier × comparator pair.

Output: outputs/agg_{comparator}__{tier}.parquet + paper/tables/agg_{...}.md
        outputs/flip_rates_current.json (headline rates for regression tests)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import click
import pandas as pd

from src.aggregator import aggregate_flips, overall_flip_rate, to_markdown
from src.loaders import iter_mas_with_log
from src.ma_types import FlipResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _row_to_flip(row: pd.Series) -> FlipResult:
    def _b(v):
        if v is None:
            return None
        try:
            if pd.isna(v):
                return None
        except (TypeError, ValueError):
            pass
        return bool(v)

    return FlipResult(
        ma_id=str(row["ma_id"]),
        baseline_method=str(row["baseline_method"]),
        comparator_method=str(row["comparator_method"]),
        tier1_sig_flip=_b(row.get("tier1_sig_flip")),
        tier2_direction_flip=_b(row.get("tier2_direction_flip")),
        tier3_mid_flip=_b(row.get("tier3_mid_flip")),
        reason_code=str(row.get("reason_code") or ""),
    )


@click.command()
@click.option("--flips", type=click.Path(exists=True, path_type=Path),
              default=Path("outputs/flips.parquet"))
@click.option("--out-dir", type=click.Path(path_type=Path),
              default=Path("outputs"))
@click.option("--tables-dir", type=click.Path(path_type=Path),
              default=Path("paper/tables"))
@click.option("--max-reviews", type=int, default=None,
              help="Match the --max-reviews used upstream")
def main(flips: Path, out_dir: Path, tables_dir: Path, max_reviews: int | None) -> None:
    fdf = pd.read_parquet(flips)
    logger.info("loaded %d flip rows", len(fdf))

    meta = pd.DataFrame([
        {"ma_id": m.ma_id, "outcome_type": m.outcome_type,
         "reproducibility_status": m.reproducibility_status, "k": m.k}
        for m in iter_mas_with_log(max_reviews=max_reviews).mas
    ])

    out_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    headline: dict[str, float] = {}

    for comparator in sorted(fdf["comparator_method"].unique()):
        sub = fdf[fdf["comparator_method"] == comparator]
        flips_list = [_row_to_flip(r) for _, r in sub.iterrows()]
        for tier in ("tier1_sig_flip", "tier2_direction_flip", "tier3_mid_flip"):
            df = aggregate_flips(flips_list, meta, tier=tier)
            key = f"{comparator}__{tier}"
            df.to_parquet(out_dir / f"agg_{key}.parquet", index=False)
            (tables_dir / f"agg_{key}.md").write_text(to_markdown(df), encoding="utf-8")
            rate = overall_flip_rate(df)
            if not pd.isna(rate):
                headline_key = f"{comparator}__{tier}_rate"
                headline[headline_key] = float(rate)
                logger.info("%s %s overall: %.3f", comparator, tier, rate)

    (out_dir / "flip_rates_current.json").write_text(
        json.dumps(headline, indent=2), encoding="utf-8"
    )
    logger.info("wrote %d strata tables + flip_rates_current.json", len(headline))


if __name__ == "__main__":
    main()
