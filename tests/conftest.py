"""Shared pytest fixtures.

Path fixtures resolve via env var, then src/paths_local.py, then None.
Tests that require external data skip if the fixture resolves to None or
a missing directory — keeps CI green where the Pairwise70 corpus is not
available.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

try:
    from src.paths_local import (  # type: ignore[import-not-found]
        DEFAULT_METAAUDIT as _DEFAULT_METAAUDIT,
        DEFAULT_PAIRWISE70 as _DEFAULT_PAIRWISE70,
        DEFAULT_REPRO_FLOOR as _DEFAULT_REPRO_FLOOR,
    )
except ImportError:
    _DEFAULT_PAIRWISE70 = _DEFAULT_METAAUDIT = _DEFAULT_REPRO_FLOOR = None


def _resolve(env_var: str, fallback: Path | None) -> Path | None:
    val = os.environ.get(env_var)
    if val:
        return Path(val)
    return fallback


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def pairwise70_dir() -> Path | None:
    return _resolve("PAIRWISE70_DIR", _DEFAULT_PAIRWISE70)


@pytest.fixture(scope="session")
def metaaudit_dir() -> Path | None:
    return _resolve("METAAUDIT_DIR", _DEFAULT_METAAUDIT)


@pytest.fixture(scope="session")
def repro_floor_atlas_dir() -> Path | None:
    return _resolve("REPRO_FLOOR_ATLAS_DIR", _DEFAULT_REPRO_FLOOR)


@pytest.fixture(scope="session")
def atlas_csv(repro_floor_atlas_dir: Path | None) -> Path | None:
    if repro_floor_atlas_dir is None:
        return None
    return repro_floor_atlas_dir / "outputs" / "atlas.csv"


@pytest.fixture(scope="session")
def mid_lookup_path(repo_root: Path) -> Path:
    return repo_root / "data" / "mid_lookup.yaml"


@pytest.fixture(scope="session")
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests" / "fixtures"
