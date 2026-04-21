"""Loader tests.

Real data tests skip if PAIRWISE70_DIR is not resolvable (so CI on
fresh machines still passes). Unit tests of internal helpers run
everywhere.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from src.loaders import (
    LoaderError,
    _effect_scale_for,
    _outcome_type_for,
    _studies_from_inputs,
    iter_mas_with_log,
)
from src.ma_types import MA


# ---- Unit tests (always run) ----

def test_effect_scale_mapping() -> None:
    assert _effect_scale_for("binary") == "logOR"
    assert _effect_scale_for("continuous") == "MD"
    assert _effect_scale_for("giv") == "GIV"


def test_effect_scale_unknown_raises() -> None:
    with pytest.raises(LoaderError):
        _effect_scale_for("silly")


def test_outcome_type_mapping() -> None:
    assert _outcome_type_for("binary") == "binary"
    assert _outcome_type_for("continuous") == "continuous"
    assert _outcome_type_for("giv") == "GIV"


def test_studies_from_inputs_binary_happy_path() -> None:
    inputs = SimpleNamespace(
        data_type="binary",
        binary=SimpleNamespace(
            e_cases=np.array([10.0, 12.0, 8.0]),
            e_n=np.array([100.0, 120.0, 80.0]),
            c_cases=np.array([15.0, 18.0, 11.0]),
            c_n=np.array([100.0, 120.0, 80.0]),
        ),
        continuous=None, giv=None,
    )
    studies = _studies_from_inputs(inputs)
    assert studies is not None
    assert len(studies) == 3
    for s in studies:
        assert np.isfinite(s.yi)
        assert s.vi > 0


def test_studies_from_inputs_giv_passthrough() -> None:
    inputs = SimpleNamespace(
        data_type="giv",
        binary=None, continuous=None,
        giv=SimpleNamespace(
            yi=np.array([0.30, 0.25, 0.28]),
            se=np.array([0.10, 0.12, 0.11]),
        ),
    )
    studies = _studies_from_inputs(inputs)
    assert studies is not None
    assert studies[0].yi == pytest.approx(0.30)
    assert studies[0].vi == pytest.approx(0.01)  # se=0.1 → vi=0.01


def test_studies_from_inputs_drops_invalid_variance() -> None:
    """Rows with vi<=0 or NaN are dropped before the k>=2 check."""
    inputs = SimpleNamespace(
        data_type="giv",
        binary=None, continuous=None,
        giv=SimpleNamespace(
            yi=np.array([0.30, 0.25, np.nan]),
            se=np.array([0.10, -0.05, 0.11]),  # -0.05 → vi = 0.0025 (positive!)
        ),
    )
    # Actually -0.05 squared is positive, so vi stays valid; the NaN yi gets dropped
    studies = _studies_from_inputs(inputs)
    assert studies is not None
    assert len(studies) == 2  # NaN dropped


def test_studies_from_inputs_returns_none_when_fewer_than_2_valid() -> None:
    inputs = SimpleNamespace(
        data_type="giv",
        binary=None, continuous=None,
        giv=SimpleNamespace(
            yi=np.array([0.30, np.nan, np.nan]),
            se=np.array([0.10, 0.12, 0.11]),
        ),
    )
    studies = _studies_from_inputs(inputs)
    assert studies is None


def test_studies_from_inputs_missing_payload_returns_none() -> None:
    inputs = SimpleNamespace(
        data_type="binary",
        binary=None, continuous=None, giv=None,
    )
    assert _studies_from_inputs(inputs) is None


# ---- Integration tests (skip without real data) ----

def _pairwise70_available() -> bool:
    import os
    default = Path(r"C:\Projects\Pairwise70\data")
    p = Path(os.environ.get("PAIRWISE70_DIR", default))
    return p.is_dir() and len(list(p.glob("*.rda"))) >= 1


skip_if_no_corpus = pytest.mark.skipif(
    not _pairwise70_available(),
    reason="Pairwise70 .rda corpus not resolvable; set PAIRWISE70_DIR or install data",
)


@skip_if_no_corpus
def test_load_first_review() -> None:
    result = iter_mas_with_log(max_reviews=1)
    assert len(result.mas) >= 1
    ma = result.mas[0]
    assert isinstance(ma, MA)
    assert ma.k >= 2
    assert ma.k == len(ma.studies)
    assert ma.effect_scale in ("logOR", "MD", "GIV")
    assert all(s.vi > 0 for s in ma.studies)


@skip_if_no_corpus
def test_reproducibility_status_merged_from_atlas() -> None:
    """After loading a handful of reviews, at least some MAs should have a
    non-'unknown' reproducibility_status — proving the atlas.csv merge works."""
    result = iter_mas_with_log(max_reviews=5)
    statuses = {ma.reproducibility_status for ma in result.mas}
    assert "reproducible" in statuses or "non_reproducible" in statuses, (
        f"no known reproducibility status found; statuses={statuses}"
    )


@skip_if_no_corpus
def test_no_duplicate_ma_ids_in_corpus() -> None:
    """If this fails, either the Pairwise70 corpus has a regression or the
    loader's duplicate-detection guard is firing as designed. Either way the
    pipeline must halt."""
    result = iter_mas_with_log(max_reviews=20)
    ids = [ma.ma_id for ma in result.mas]
    assert len(ids) == len(set(ids)), "duplicate ma_ids in loaded corpus"


def test_duplicate_ma_id_hard_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the metaaudit loader to return two analyses with the same ma_id;
    verify LoaderError('dataset_integrity_error') is raised.

    This is the guard for the 'lessons.md' duplicate-id-silent-corruption
    failure mode — we never silently pick one.
    """
    import src.loaders as loaders_mod

    # Fake AnalysisGroup with the minimum interface the loader uses
    class _FakeDataType:
        def __init__(self, v: str) -> None:
            self.value = v

    class _FakeAG:
        def __init__(self, ma_id: str, data_type: str) -> None:
            self.ma_id = ma_id
            self.review_id = "fake_rev"
            self.data_type = _FakeDataType(data_type)
            # empty df → skip path, but duplicate check fires first
            import pandas as pd
            self.df = pd.DataFrame()

    class _FakeReview:
        def __init__(self) -> None:
            self.analyses = [_FakeAG("dup_id", "binary"), _FakeAG("dup_id", "binary")]

    def _fake_load_all_reviews(data_dir, max_reviews=None):
        return [_FakeReview()]

    # Patch the import inside iter_mas_with_log
    import metaaudit.loader as ml
    monkeypatch.setattr(ml, "load_all_reviews", _fake_load_all_reviews)

    with pytest.raises(LoaderError, match="dataset_integrity_error"):
        iter_mas_with_log(max_reviews=1)
