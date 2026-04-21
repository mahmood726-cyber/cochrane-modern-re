"""Preflight: verify the environment is ready BEFORE running any other test.

Per rules.md 'verification readiness preflight': check R, metafor, bayesmeta,
jsonlite, Rscript invocable, Pairwise70 dir resolves, MetaAudit dir resolves,
atlas.csv present, MID YAML parses. Downstream tests are meaningless if any
of these fail — surface it early.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from ruamel.yaml import YAML


def _find_rscript() -> str:
    rscript = shutil.which("Rscript")
    if rscript:
        return rscript
    fallback = r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe"
    if Path(fallback).exists():
        return fallback
    pytest.skip("Rscript not found on PATH or at default Windows path")


def _run_rscript(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_find_rscript(), "-e", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def test_rscript_invokable() -> None:
    result = _run_rscript('cat(R.version.string)')
    assert result.returncode == 0, result.stderr
    assert "R version 4.5" in result.stdout, f"Expected R 4.5.x; got: {result.stdout!r}"


def test_metafor_loadable() -> None:
    result = _run_rscript('suppressMessages(library(metafor)); cat("ok")')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_bayesmeta_loadable() -> None:
    result = _run_rscript('suppressMessages(library(bayesmeta)); cat("ok")')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_jsonlite_loadable() -> None:
    result = _run_rscript('suppressMessages(library(jsonlite)); cat("ok")')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_pairwise70_dir_resolves(pairwise70_dir: Path | None) -> None:
    if pairwise70_dir is None:
        pytest.skip("PAIRWISE70_DIR not set and no paths_local.py — data-dependent test")
    assert pairwise70_dir.is_dir(), (
        f"PAIRWISE70_DIR does not resolve to a directory: {pairwise70_dir}. "
        "Set env var PAIRWISE70_DIR or run scripts/prereq_check.py."
    )
    rda_files = list(pairwise70_dir.glob("*.rda"))
    assert len(rda_files) >= 100, (
        f"PAIRWISE70_DIR has only {len(rda_files)} .rda files; expected 100+."
    )


def test_metaaudit_dir_resolves(metaaudit_dir: Path | None) -> None:
    if metaaudit_dir is None:
        pytest.skip("METAAUDIT_DIR not set and no paths_local.py — data-dependent test")
    assert metaaudit_dir.is_dir(), f"METAAUDIT_DIR does not resolve: {metaaudit_dir}"
    for required in ("__init__.py", "loader.py", "recompute.py"):
        assert (metaaudit_dir / required).exists(), (
            f"METAAUDIT_DIR missing required file: {required}"
        )


def test_atlas_csv_present(atlas_csv: Path | None) -> None:
    if atlas_csv is None:
        pytest.skip("REPRO_FLOOR_ATLAS_DIR not set — data-dependent test")
    assert atlas_csv.exists(), (
        f"repro-floor-atlas atlas.csv missing: {atlas_csv}. "
        "Set REPRO_FLOOR_ATLAS_DIR or run repro-floor-atlas scripts/run_atlas.py."
    )


def test_mid_yaml_parses_with_schema(mid_lookup_path: Path) -> None:
    assert mid_lookup_path.exists(), f"MID lookup missing: {mid_lookup_path}"
    yaml = YAML(typ="safe")
    with mid_lookup_path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    assert isinstance(data, dict), "MID YAML must be a top-level dict"
    assert len(data) > 0, "MID YAML must have at least one entry"
    for key, entry in data.items():
        assert isinstance(entry, dict), f"{key}: entry must be a dict"
        assert "mid" in entry, f"{key}: missing 'mid' field"
        assert isinstance(entry["mid"], (int, float)), f"{key}: 'mid' must be numeric"
        assert "scale" in entry, f"{key}: missing 'scale' field"
        assert entry["scale"] in ("natural", "sd_units"), (
            f"{key}: scale must be 'natural' or 'sd_units', got {entry['scale']!r}"
        )
        assert "source" in entry, f"{key}: missing 'source' field"
