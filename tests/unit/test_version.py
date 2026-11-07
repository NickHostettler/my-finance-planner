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


def test_version_falls_back_when_package_is_not_installed(monkeypatch):
    import importlib
    import importlib.metadata

    def not_installed(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", not_installed)
    try:
        assert importlib.reload(personal_finance).__version__ == "0+unknown"
    finally:
        monkeypatch.undo()
        importlib.reload(personal_finance)
    assert personal_finance.__version__ == version("swiss-personal-finance")


def test_python_dash_m_starts_the_dashboard(monkeypatch):
    import runpy

    from personal_finance import dashboard

    calls = []
    monkeypatch.setattr(dashboard, "main", lambda: calls.append("started"))

    runpy.run_module("personal_finance", run_name="not_main")
    assert calls == []
    runpy.run_module("personal_finance", run_name="__main__")
    assert calls == ["started"]
