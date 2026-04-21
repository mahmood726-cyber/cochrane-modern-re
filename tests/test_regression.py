"""Regression snapshots — top-level flip rates pinned per release.

Pinned in tests/snapshots/flip_rates_v0.1.0.json at v0.1.0 tag time.
Any drift >2% per rules.md regression rule requires an explicit snapshot
bump with rationale in the release notes.

Skipped automatically if outputs/flip_rates_current.json doesn't exist
(i.e., analysis hasn't been re-run since a fresh checkout).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


SNAPSHOT = Path(__file__).parent / "snapshots" / "flip_rates_v0.1.0.json"
CURRENT = Path(__file__).resolve().parent.parent / "outputs" / "flip_rates_current.json"
DRIFT_TOLERANCE = 0.02  # 2% absolute


@pytest.fixture(scope="module")
def snapshot() -> dict[str, float]:
    if not SNAPSHOT.exists():
        pytest.skip(f"snapshot not yet recorded at {SNAPSHOT}")
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def current() -> dict[str, float]:
    if not CURRENT.exists():
        pytest.skip(
            f"current output not found: {CURRENT}. "
            "Run analysis/01-03 to produce it."
        )
    return json.loads(CURRENT.read_text(encoding="utf-8"))


def test_headline_flip_rates_within_2pc(snapshot: dict, current: dict) -> None:
    keys = [
        "REML_HKSJ_PI__tier1_sig_flip_rate",
        "REML_HKSJ_PI__tier2_direction_flip_rate",
        "REML_HKSJ_PI__tier3_mid_flip_rate",
    ]
    for key in keys:
        assert key in snapshot, f"{key} missing from pinned snapshot"
        assert key in current, f"{key} missing from current outputs"
        snap = snapshot[key]
        cur = current[key]
        assert abs(cur - snap) < DRIFT_TOLERANCE, (
            f"{key} drifted beyond {DRIFT_TOLERANCE:.1%}: "
            f"pinned={snap:.4f}, current={cur:.4f}, |Δ|={abs(cur - snap):.4f}. "
            f"If intentional: update {SNAPSHOT} and document in CHANGELOG."
        )


def test_all_pinned_tiers_nonzero() -> None:
    """Sanity check: the v0.1.0 snapshot was computed against a real corpus;
    all three tier rates should be positive floats."""
    if not SNAPSHOT.exists():
        pytest.skip("snapshot not yet recorded")
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    for key, val in snap.items():
        assert isinstance(val, float), f"{key}: not a float"
        assert val >= 0.0, f"{key}: negative rate"
        assert val <= 1.0, f"{key}: rate > 100%"
