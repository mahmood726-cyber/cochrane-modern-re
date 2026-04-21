"""Shared pytest fixtures.

Path fixtures respect the env-var-driven layout established in Task 0.3.
See data/README.md for full provenance.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

_DEFAULT_PAIRWISE70 = Path(r"C:\Projects\Pairwise70\data")
_DEFAULT_METAAUDIT = Path(r"C:\MetaAudit\metaaudit")
_DEFAULT_REPRO_FLOOR = Path(r"C:\Projects\repro-floor-atlas")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def pairwise70_dir() -> Path:
    return Path(os.environ.get("PAIRWISE70_DIR", _DEFAULT_PAIRWISE70))


@pytest.fixture(scope="session")
def metaaudit_dir() -> Path:
    return Path(os.environ.get("METAAUDIT_DIR", _DEFAULT_METAAUDIT))


@pytest.fixture(scope="session")
def repro_floor_atlas_dir() -> Path:
    return Path(os.environ.get("REPRO_FLOOR_ATLAS_DIR", _DEFAULT_REPRO_FLOOR))


@pytest.fixture(scope="session")
def atlas_csv(repro_floor_atlas_dir: Path) -> Path:
    return repro_floor_atlas_dir / "outputs" / "atlas.csv"


@pytest.fixture(scope="session")
def mid_lookup_path(repo_root: Path) -> Path:
    return repo_root / "data" / "mid_lookup.yaml"


@pytest.fixture(scope="session")
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests" / "fixtures"
