"""Classify flips for DL-vs-REML_HKSJ_PI and DL-vs-bayesmeta_HN pairs.

Usage:
    python analysis/02_classify_flips.py
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

import click
import pandas as pd
from ruamel.yaml import YAML

from src.flip_classifier import classify_flip
from src.loaders import iter_mas_with_log
from src.ma_types import MethodResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _row_to_method_result(ma_id: str, row: pd.Series) -> MethodResult:
    """Reconstruct MethodResult from a parquet row. Handles NaN -> None.

    ma_id is passed separately because after set_index('ma_id') the row
    Series has no 'ma_id' field.
    """
    def _n(v):
        if v is None:
            return None
        try:
            if pd.isna(v):
                return None
        except (TypeError, ValueError):
            pass
        return v

    return MethodResult(
        ma_id=ma_id,
        method=str(row["method"]),
        estimate=_n(row.get("estimate")),
        se=_n(row.get("se")),
        ci_lo=_n(row.get("ci_lo")),
        ci_hi=_n(row.get("ci_hi")),
        tau2=_n(row.get("tau2")),
        i2=_n(row.get("i2")),
        pi_lo=_n(row.get("pi_lo")),
        pi_hi=_n(row.get("pi_hi")),
        k_effective=int(row["k_effective"]),
        converged=bool(row["converged"]),
        rhat=_n(row.get("rhat")),
        ess=_n(row.get("ess")),
        reason_code=str(row.get("reason_code") or ""),
    )


@click.command()
@click.option("--method-results", type=click.Path(exists=True, path_type=Path),
              default=Path("outputs/method_results.parquet"))
@click.option("--mid", type=click.Path(exists=True, path_type=Path),
              default=Path("data/mid_lookup.yaml"))
@click.option("--out", type=click.Path(path_type=Path),
              default=Path("outputs/flips.parquet"))
@click.option("--max-reviews", type=int, default=None,
              help="Match the --max-reviews used in 01_run_methods")
def main(method_results: Path, mid: Path, out: Path, max_reviews: int | None) -> None:
    df = pd.read_parquet(method_results)
    logger.info("loaded %d method-result rows", len(df))

    yaml = YAML(typ="safe")
    with mid.open("r", encoding="utf-8") as f:
        mid_table = yaml.load(f)

    # Need MA metadata (outcome_code, effect_scale) to classify
    mas_by_id = {m.ma_id: m for m in iter_mas_with_log(max_reviews=max_reviews).mas}

    by_method = {name: g.set_index("ma_id") for name, g in df.groupby("method")}
    if "DL" not in by_method:
        raise click.ClickException("No DL rows in method results — baseline missing.")

    flip_rows: list[dict] = []
    for comparator_name in ("REML_HKSJ_PI", "bayesmeta_HN"):
        if comparator_name not in by_method:
            logger.warning("comparator %s missing from method_results; skipping",
                           comparator_name)
            continue
        for ma_id, ma in mas_by_id.items():
            if ma_id not in by_method["DL"].index:
                continue
            if ma_id not in by_method[comparator_name].index:
                continue
            baseline = _row_to_method_result(ma_id, by_method["DL"].loc[ma_id])
            comparator = _row_to_method_result(ma_id, by_method[comparator_name].loc[ma_id])
            flip = classify_flip(
                baseline, comparator,
                effect_scale=ma.effect_scale,
                outcome_code=ma.outcome_code,
                mid_table=mid_table,
            )
            flip_rows.append(asdict(flip))

    out.parent.mkdir(parents=True, exist_ok=True)
    flip_df = pd.DataFrame(flip_rows)
    flip_df.to_parquet(out, index=False)
    logger.info("wrote %d flip rows to %s", len(flip_df), out)
    if not flip_df.empty:
        for comparator_name, g in flip_df.groupby("comparator_method"):
            for tier in ("tier1_sig_flip", "tier2_direction_flip", "tier3_mid_flip"):
                nonnull = g[tier].dropna()
                if len(nonnull):
                    rate = (nonnull == True).sum() / len(nonnull)  # noqa: E712
                    logger.info("  %s %s: %d/%d = %.1f%%",
                                comparator_name, tier, int((nonnull == True).sum()),  # noqa: E712
                                len(nonnull), 100 * rate)


if __name__ == "__main__":
    main()
