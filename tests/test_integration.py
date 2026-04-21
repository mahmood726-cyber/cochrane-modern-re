"""End-to-end integration smoke test.

Loads a small slice of the real Pairwise70 corpus, runs every pipeline stage
in sequence, and pins a flip-count snapshot so drift is caught by CI.

Skipped automatically if PAIRWISE70_DIR isn't resolvable.

Budget: <300 s (Bayesian is slow; skipped from smoke by default).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest
from ruamel.yaml import YAML

from src.aggregator import aggregate_flips, overall_flip_rate
from src.dashboard import build_dashboard
from src.flip_classifier import classify_flip
from src.loaders import iter_mas_with_log
from src.methods import run_batch


_SNAPSHOT = Path(__file__).parent / "fixtures" / "integration_smoke_snapshot.json"
_DEFAULT_PAIRWISE70 = Path(r"C:\Projects\Pairwise70\data")


def _pairwise70_available() -> bool:
    p = Path(os.environ.get("PAIRWISE70_DIR", _DEFAULT_PAIRWISE70))
    return p.is_dir() and len(list(p.glob("*.rda"))) >= 1


skip_if_no_corpus = pytest.mark.skipif(
    not _pairwise70_available(),
    reason="Pairwise70 corpus not resolvable",
)


@skip_if_no_corpus
def test_end_to_end_smoke_first_six_reviews(
    mid_lookup_path: Path, tmp_path: Path
) -> None:
    # 1. Load
    result = iter_mas_with_log(max_reviews=6)
    mas = result.mas
    assert len(mas) >= 5, f"expected >=5 MAs from 6 reviews, got {len(mas)}"

    yaml = YAML(typ="safe")
    with mid_lookup_path.open("r", encoding="utf-8") as f:
        mid_table = yaml.load(f)

    # 2. Batch methods by effect_scale — only the fast deterministic ones
    #    (bayesmeta is too slow to include in smoke; covered in its own tests).
    by_scale: dict[str, list] = {}
    for m in mas:
        by_scale.setdefault(m.effect_scale, []).append(m)

    dl_results: dict[str, object] = {}
    hksj_results: dict[str, object] = {}
    for scale, group in by_scale.items():
        for r in run_batch(method="DL", effect_scale=scale, mas=group):
            dl_results[r.ma_id] = r
        for r in run_batch(method="REML_HKSJ_PI", effect_scale=scale, mas=group):
            hksj_results[r.ma_id] = r

    assert len(dl_results) == len(mas)
    assert len(hksj_results) == len(mas)

    # 3. Flip classification
    flips = []
    for m in mas:
        flip = classify_flip(
            dl_results[m.ma_id], hksj_results[m.ma_id],
            effect_scale=m.effect_scale,
            outcome_code=m.outcome_code,
            mid_table=mid_table,
        )
        flips.append(flip)
    assert len(flips) == len(mas)

    # 4. Aggregate
    meta = pd.DataFrame([
        {"ma_id": m.ma_id, "outcome_type": m.outcome_type,
         "reproducibility_status": m.reproducibility_status, "k": m.k}
        for m in mas
    ])
    tier1 = aggregate_flips(flips, meta, tier="tier1_sig_flip")
    tier2 = aggregate_flips(flips, meta, tier="tier2_direction_flip")
    tier3 = aggregate_flips(flips, meta, tier="tier3_mid_flip")

    assert not tier1.empty
    assert not tier2.empty
    # tier3 will have all-NA flips because outcome_code='unknown_outcome'
    # corpus-wide in v0.1 (documented follow-on work)
    assert int(tier3["n_flips"].sum()) == 0, "tier3 must be all-NA until MID mapping is built"

    # 5. Dashboard renders
    out = tmp_path / "index.html"
    build_dashboard(
        tier1_df=tier1, tier2_df=tier2, tier3_df=tier3,
        headline_rate=overall_flip_rate(tier1),
        n_mas=len(mas),
        n_reviews=len({m.review_id for m in mas}),
        version="smoke", output=out,
    )
    assert out.exists()
    assert "Flip Atlas" in out.read_text(encoding="utf-8")

    # 6. Snapshot the headline counts for regression detection
    summary = {
        "n_mas": len(mas),
        "n_reviews": len({m.review_id for m in mas}),
        "tier1_flips": int(tier1["n_flips"].sum()),
        "tier1_comparable": int(tier1["n_comparable"].sum()),
        "tier2_flips": int(tier2["n_flips"].sum()),
        "tier2_comparable": int(tier2["n_comparable"].sum()),
    }
    if not _SNAPSHOT.exists():
        _SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        _SNAPSHOT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        pytest.skip(f"snapshot created at {_SNAPSHOT}; rerun to verify stability")

    expected = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    for key in ("n_mas", "n_reviews", "tier1_flips", "tier1_comparable",
                "tier2_flips", "tier2_comparable"):
        assert summary[key] == expected[key], (
            f"{key} drifted: expected {expected[key]}, got {summary[key]}. "
            f"If intentional, delete {_SNAPSHOT} and rerun."
        )
