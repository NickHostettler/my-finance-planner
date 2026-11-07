"""The package version has a single source of truth: pyproject.toml."""

import tomllib
from importlib.metadata import version
from pathlib import Path

import personal_finance

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_version_matches_pyproject_and_installed_metadata():
    declared = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]

    assert personal_finance.__version__ == declared
    assert version("swiss-personal-finance") == declared
